from typing import Iterator, Tuple, List
from operator import itemgetter

from spyll.hunspell import data
import spyll.hunspell.algo.string_metrics as sm
from spyll.hunspell.algo.util import ScoredArray


MAX_ROOTS = 100
MAX_WORDS = 100
MAX_GUESSES = 200

MAXNGRAMSUGS = 4
MAXPHONSUGS = 2
MAXCOMPOUNDSUGS = 3


def ngram_suggest(word: str, *, roots, forms_producer, maxdiff: int, onlymaxdiff=False) -> Iterator[str]:
    # TODO: lowering depends on BMP of word, true by default
    # low = True

    # exhaustively search through all root words
    # keeping track of the MAX_ROOTS most similar root words
    root_scores = ScoredArray[data.dic.Word](MAX_ROOTS)

    for dword in roots:
        if abs(len(dword.stem) - len(word)) > 4:
            continue
        # TODO: more exceptions -- lift to suggest
        # ...word is nocap and root is initcap (though, a lot of "unless...")
        # ...?onlyupcase flag

        score = root_score(word, dword.stem)
        if dword.phonetic():
            for variant in dword.phonetic():
                score = max(score, root_score(word, variant))

        root_scores.push(dword, score)

    threshold = detect_threshold(word)

    # now expand affixes on each of these root words and
    # and use length adjusted ngram scores to select
    # possible suggestions
    guess_scores = ScoredArray[Tuple[str, str]](MAX_GUESSES)
    for (root, _) in root_scores.result():
        if root.phonetic():
            for variant in root.phonetic():
                score = rough_affix_score(word, variant)
                if score > threshold:
                    guess_scores.push((variant, root.stem), score)

        for form in forms_producer(root, word):
            score = rough_affix_score(word, form.lower())
            if score > threshold:
                guess_scores.push((form, form), score)

    # now we are done generating guesses
    # sort in order of decreasing score
    guesses = sorted(guess_scores.result(), key=itemgetter(1), reverse=True)

    fact = (10.0 - maxdiff) / 5.0 if maxdiff >= 0 else 1.0

    # weight suggestions with a similarity index, based on
    # the longest common subsequent algorithm and resort
    guesses2 = [
        (real, detailed_affix_score(word, compared.lower(), fact, base=score))
        for ((compared, real), score) in guesses
    ]

    guesses2 = sorted(guesses2, key=itemgetter(1), reverse=True)

    yield from filter_guesses(guesses2, onlymaxdiff=onlymaxdiff)


def filter_guesses(guesses: List[Tuple[str, float]], *, onlymaxdiff=True) -> Iterator[str]:
    same = False
    found = 0

    for (value, score) in guesses:
        if same and score <= 1000:
            continue

        # leave only excellent suggestions, if exists
        if score > 1000:
            same = True
        elif score < -100:  # FIXME: what's that? Seems related to last line of score...
            same = True
            if found > 0 and onlymaxdiff:
                continue

        found += 1

        # TODO: 1. guessorig vs guess; 2. don't suggest what already was there...
        yield value


def detect_threshold(word: str) -> float:
    # find minimum threshold for a passable suggestion
    # mangle original word three differnt ways
    # and score them to generate a minimum acceptable score
    thresh = 0

    for sp in range(1, 4):
        mangled = list(word)
        for pos in range(sp, len(word), 4):
            mangled[pos] = '*'

        mangled_word = ''.join(mangled).lower()

        thresh += sm.ngram(len(word), word, mangled_word, any_mismatch=True)

    return thresh // 3 - 1


def root_score(word1: str, word2: str) -> float:
    return sm.ngram(3, word1, word2.lower(), longer_worse=True) + \
          sm.leftcommonsubstring(word1, word2.lower())


def rough_affix_score(word1: str, word2: str) -> float:
    return sm.ngram(len(word1), word1, word2, any_mismatch=True) + \
         sm.leftcommonsubstring(word1, word2)


def detailed_affix_score(word1: str, word2: str, fact: float, *, base: float) -> float:
    lcs = sm.lcslen(word1, word2)

    # same characters with different casing
    if len(word1) == len(word2) and len(word1) == lcs:
        return base + 2000

    # using 2-gram instead of 3, and other weightening
    re = sm.ngram(2, word1, word2, any_mismatch=True, weighted=True) + \
        sm.ngram(2, word2, word1, any_mismatch=True, weighted=True)

    ngram_score = sm.ngram(4, word1, word2, any_mismatch=True)
    leftcommon_score = sm.leftcommonsubstring(word1, word2.lower())

    cps, is_swap = sm.commoncharacterpositions(word1, word2.lower())

    return (
        # length of longest common subsequent minus length difference
        2 * lcs - abs(len(word1) - len(word2)) +
        # weight length of the left common substring
        leftcommon_score +
        # weight equal character positions
        (1 if cps else 0) +
        # swap character (not neighboring)
        (10 if is_swap else 0) +
        # ngram
        ngram_score +
        # weighted ngrams
        re +
        (-1000 if re < (len(word1) + len(word2)) * fact else 0)
    )
