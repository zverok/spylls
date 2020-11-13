from typing import Iterator, Tuple, List, Set
from operator import itemgetter
import heapq

from spyll.hunspell import data
import spyll.hunspell.algo.string_metrics as sm


MAX_ROOTS = 100
MAX_WORDS = 100
MAX_GUESSES = 200

MAXNGRAMSUGS = 4
MAXPHONSUGS = 2
MAXCOMPOUNDSUGS = 3


def ngram_suggest(word: str, *,
                  roots, aff, known: Set[str], maxdiff: int, onlymaxdiff=False) -> Iterator[str]:
    # TODO: lowering depends on BMP of word, true by default

    # exhaustively search through all root words
    # keeping track of the MAX_ROOTS most similar root words
    root_scores: List[Tuple[float, str, data.dic.Word]] = []

    for dword in roots:
        if abs(len(dword.stem) - len(word)) > 4:
            continue
        # TODO: more exceptions -- lift to suggest
        # ...word is nocap and root is initcap (though, a lot of "unless...")
        # ...?onlyupcase flag

        score = root_score(word, dword.stem)
        if dword.alt_spellings:
            for variant in dword.alt_spellings:
                score = max(score, root_score(word, variant))

        if len(root_scores) > MAX_ROOTS:
            heapq.heappushpop(root_scores, (score, dword.stem, dword))
        else:
            heapq.heappush(root_scores, (score, dword.stem, dword))

    threshold = detect_threshold(word)

    # now expand affixes on each of these root words and
    # and use length adjusted ngram scores to select
    # possible suggestions
    guess_scores: List[Tuple[float, str, str]] = []
    for (_, _, root) in heapq.nlargest(MAX_ROOTS, root_scores):
        if root.alt_spellings:
            for variant in root.alt_spellings:
                score = rough_affix_score(word, variant)
                if score > threshold:
                    heapq.heappush(guess_scores, (score, variant, root.stem))

        for form in forms_for(aff, root, word):
            score = rough_affix_score(word, form.lower())
            if score > threshold:
                heapq.heappush(guess_scores, (score, form, form))

    # now we are done generating guesses
    # sort in order of decreasing score
    guesses = heapq.nlargest(MAX_GUESSES, guess_scores)

    fact = (10.0 - maxdiff) / 5.0 if maxdiff >= 0 else 1.0

    # weight suggestions with a similarity index, based on
    # the longest common subsequent algorithm and resort
    guesses2 = [
        (real, detailed_affix_score(word, compared.lower(), fact, base=score))
        for (score, compared, real) in guesses
    ]

    guesses2 = sorted(guesses2, key=itemgetter(1), reverse=True)

    yield from filter_guesses(guesses2, known=known, onlymaxdiff=onlymaxdiff)


def filter_guesses(guesses: List[Tuple[str, float]], *, known: Set[str], onlymaxdiff=True) -> Iterator[str]:
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
            if found > 0 or onlymaxdiff:
                continue

        if not any(known_word in value for known_word in known):
            found += 1

            yield value


def detect_threshold(word: str) -> float:
    # find minimum threshold for a passable suggestion
    # mangle original word three differnt ways
    # and score them to generate a minimum acceptable score
    thresh = 0.0

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


def forms_for(aff: data.Aff, word: data.dic.Word, candidate: str):
    # word without prefixes/suffixes is also present
    res = [word.stem]

    suffixes = [
        suffix
        for flag in word.flags
        for suffix in aff.SFX.get(flag, [])
        if suffix.cond_regexp.search(word.stem) and candidate.endswith(suffix.add)
    ]
    prefixes = [
        prefix
        for flag in word.flags
        for prefix in aff.PFX.get(flag, [])
        if prefix.cond_regexp.search(word.stem) and candidate.startswith(prefix.add)
    ]

    cross = [
        (prefix, suffix)
        for prefix in prefixes
        for suffix in suffixes
        if suffix.crossproduct and prefix.crossproduct
    ]

    for suf in suffixes:
        # FIXME: this things should be more atomic
        root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
        res.append(root + suf.add)

    for pref, suf in cross:
        root = word.stem[len(pref.strip):-len(suf.strip)] if suf.strip else word.stem[len(pref.strip):]
        res.append(pref.add + root + suf.add)

    for pref in prefixes:
        root = word.stem[len(pref.strip):]
        res.append(pref.add + root)

    return res
