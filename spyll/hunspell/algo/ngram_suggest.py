from typing import Iterator, Tuple, TypeVar, Generic, List, Optional

from spyll.hunspell import data
import spyll.hunspell.algo.string_metrics as sm


MAX_ROOTS = 100
MAX_WORDS = 100
MAX_GUESSES = 200

MAXNGRAMSUGS = 4
MAXPHONSUGS = 2
MAXCOMPOUNDSUGS = 3

Value = TypeVar('Value')


class ScoredArray(Generic[Value]):
    data: List[Tuple[Optional[Value], float]]

    def __init__(self, size: int):
        # FIXME: Can't guess how to do it with NamedTuple instead of tuple so mypy would
        # be happy :(
        self.data = [(None, -100*i) for i in range(size)]
        self.insert_at = size - 1

    def push(self, value: Value, score: float):
        if score <= self.data[self.insert_at][1]:
            return

        self.data[self.insert_at] = (value, score)

        # Next value should be inserted at the point which currently has minimum score
        # below current score
        lowest = score
        for i, cur in enumerate(self.data):
            if cur[1] < lowest:
                self.insert_at = i
                lowest = cur[1]

    def result(self) -> Iterator[Tuple[Value, float]]:
        return filter(lambda s: s[0], self.data)


def ngram_suggest(dictionary, word: str, *, maxdiff: int, onlymaxdiff=False) -> Iterator[str]:
    # TODO: lowering depends on BMP of word, true by default
    # low = True

    # TODO: if PHONE table in aff, we also look for phonetic suggestion borrowed from aspell

    # exhaustively search through all root words
    # keeping track of the MAX_ROOTS most similar root words
    root_scores = ScoredArray[data.dic.Word](MAX_ROOTS)
    for dword in dictionary.roots():
        if abs(len(dword.stem) - len(word)) > 4:
            continue
        # TODO: large skip_exceptions block
        # if lots of conditions: continue
        # Should be in fact encapsulated by dictionary

        root_scores.push(dword, root_score(word, dword.stem))

    threshold = detect_threshold(word)

    # now expand affixes on each of these root words and
    # and use length adjusted ngram scores to select
    # possible suggestions
    guess_scores = ScoredArray[str](MAX_GUESSES)
    for (root, _) in root_scores.result():
        for form in dictionary.forms_for(root):
            score = first_affix_score(word, form.lower())
            if score > threshold:
                guess_scores.push(form, score)

    # now we are done generating guesses
    # sort in order of decreasing score
    guesses = sorted(guess_scores.result(), key=lambda g: -g[1])

    guesses2 = []

    fact = 1.0
    if maxdiff >= 0:
        fact = (10.0 - maxdiff) / 5.0

    # weight suggestions with a similarity index, based on
    # the longest common subsequent algorithm and resort
    for (value, score) in guesses:
        gl = value.lower()

        sc = detailed_affix_score(word, gl, fact)
        if not sc:
            sc = score + 2000
        guesses2.append((value, sc))

    guesses2 = sorted(guesses2, key=lambda g: -g[1])

    for guess in filter_guesses(guesses2, onlymaxdiff=onlymaxdiff):
        yield guess


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
    thresh = 0.0

    for sp in range(1, 4):
        mangled = list(word)
        for pos in range(sp, len(word), 4):
            mangled[pos] = '*'

        mangled_word = ''.join(mangled).lower()

        thresh += sm.ngram(len(word), word, mangled_word, any_mismatch=True)

    return thresh / 3 - 1


def root_score(word1: str, word2: str) -> float:
    leftcommon = sm.leftcommonsubstring(word1, word2.lower())
    return sm.ngram(3, word1, word2.lower(), longer_worse=True) + leftcommon


def first_affix_score(word1: str, word2: str) -> float:
    leftcommon = sm.leftcommonsubstring(word1, word2)
    return sm.ngram(len(word1), word1, word2, any_mismatch=True) + leftcommon


def detailed_affix_score(word1: str, word2: str, fact: float) -> Optional[float]:
    lcs = sm.lcslen(word1, word2)

    # same characters with different casing
    if len(word1) == len(word2) and len(word1) == lcs:
        return None

    # using 2-gram instead of 3, and other weightening
    re = sm.ngram(2, word1, word2, any_mismatch=True, weighted=True)
    re += sm.ngram(2, word2, word1.lower(), any_mismatch=True, weighted=True)

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
