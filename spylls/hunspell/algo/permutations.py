"""
Note: names of methods in this module, if seem weird, are the same as in Hunspell's ``suggest.cxx``
to keep track of them.
"""

from typing import Iterator, Union, List, Set

from spylls.hunspell.data import aff


MAX_CHAR_DISTANCE = 4


def replchars(word: str, reptable: List[aff.RepPattern]) -> Iterator[Union[str, List[str]]]:
    """
    Uses :attr:`aff.REP <spylls.hunspell.data.aff.Aff.REP>` table (typical misspellings) to replace
    in the word provided. If the pattern's replacement contains "_", it means replacing to " " and
    yielding _two_ different hypotheses: it was one (dictionary) word "foo bar" (and should be
    checked as such) or it was words ["foo", "bar"] and should be checked separately.
    """

    if len(word) < 2 or not reptable:
        return

    for pattern in reptable:
        # TODO: compiled at aff loading
        for match in pattern.regexp.finditer(word):
            suggestion = word[:match.start()] + pattern.replacement.replace('_', ' ') + word[match.end():]
            yield suggestion
            if ' ' in suggestion:
                yield suggestion.split(' ', 2)


def mapchars(word: str, maptable: List[Set[str]]) -> Iterator[str]:
    """
    Uses :attr:`aff.MAP <spylls.hunspell.data.aff.Aff.MAP>` table ( sets of potentially similar chars)
    and tries to replace them recursively. E.g., assuming ``MAP`` has entry ``aáã``, and we have
    a misspelling "anarchia", ``mapchars`` will do this:

    >>> [*pmt.mapchars("anarchia", ['aáã'])]
    ['ánarchia',
     'ánárchia',
     'ánárchiá',
     'ánárchiã',
     'ánãrchia',
     'ánãrchiá',
     'ánãrchiã',
     'ãnarchia',
     'ãnárchia',
     'ãnárchiá',
     'ãnárchiã',
     'ãnãrchia',
     'ãnãrchiá',
     'ãnãrchiã']
    """

    if len(word) < 2 or not maptable:
        return

    def mapchars_internal(word, start=0):
        if start >= len(word):
            return

        for options in maptable:
            for option in options:
                pos = word.find(option, start)
                if pos != -1:
                    for other in options:
                        if other == option:
                            continue
                        replaced = word[:pos] + other + word[pos+len(option):]
                        yield replaced
                        for variant in mapchars_internal(replaced, pos + 1):
                            yield variant

    for variant in mapchars_internal(word):
        yield variant


def swapchar(word: str) -> Iterator[str]:
    """
    Produces permutations with adjacent chars swapped. For short (4 or 5 letters) words produces
    also doubleswaps: ahev -> have.
    """

    if len(word) < 2:
        return

    for i in range(0, len(word) - 1):
        yield word[:i] + word[i+1] + word[i+1] + word[i+2:]

    # try double swaps for short words
    # ahev -> have, owudl -> would
    if len(word) in [4,  5]:
        yield word[1] + word[0] + (word[2] if len(word) == 5 else '') + word[-1] + word[-2]
        if len(word) == 5:
            yield word[0] + word[2] + word[1] + word[-1] + word[-2]


def longswapchar(word: str) -> Iterator[str]:
    """
    Produces permutations with non-adjacent chars swapped (up to 4 chars distance)
    """

    for first in range(0, len(word) - 2):
        for second in range(first + 2, min(first + MAX_CHAR_DISTANCE, len(word))):
            yield word[:first] + word[second] + word[first+1:second] + word[first] + word[second+1:]


def badcharkey(word: str, layout: str) -> Iterator[str]:
    """
    Produces permutations with chars replaced by adjacent chars on keyboard layout ("vat -> cat")
    or downcased (if it was accidental uppercase).

    Uses :attr:`aff.KEY <spylls.hunspell.data.aff.Aff.KEY>`
    """

    for i, c in enumerate(word):
        before = word[:i]
        after = word[i+1:]
        if c != c.upper():
            yield before + c.upper() + after

        if not layout:
            continue

        pos = layout.find(c)
        while pos != -1:
            if pos > 0 and layout[pos-1] != '|':
                yield before + layout[pos-1] + after
            if pos + 1 < len(layout) and layout[pos+1] != '|':
                yield before + layout[pos+1] + after
            pos = layout.find(c, pos+1)


def extrachar(word: str) -> Iterator[str]:
    """
    Produces permutations with one char removed in all possible positions
    """
    if len(word) < 2:
        return

    for i in range(0, len(word)):
        yield word[:i] + word[i+1:]


def forgotchar(word: str, trystring: str) -> Iterator[str]:
    """
    Produces permutations with one char inserted in all possible possitions.

    List of chars is taken from :attr:`aff.TRY <spylls.hunspell.data.aff.Aff.TRY>` -- if it is absent,
    doesn't try anything! Chars there are expected to be sorted in order of chars usage in language
    (most used characters first).
    """

    if not trystring:
        return

    for c in trystring:
        for i in range(0, len(word)):
            yield word[:i] + c + word[i:]


def movechar(word: str) -> Iterator[str]:
    """
    Produces permutations with one character moved by 2, 3 or 4 places forward or backward (not 1,
    because it is already handled by :meth:`swapchar`)
    """

    if len(word) < 2:
        return

    for frompos, char in enumerate(word):
        for topos in range(frompos + 3, min(len(word), frompos + MAX_CHAR_DISTANCE + 1)):
            yield word[:frompos] + word[frompos+1:topos] + char + word[topos:]

    for frompos in reversed(range(0, len(word))):
        for topos in reversed(range(max(0, frompos - MAX_CHAR_DISTANCE + 1), frompos - 1)):
            yield word[:topos] + word[frompos] + word[topos:frompos] + word[frompos+1:]


def badchar(word: str, trystring: str) -> Iterator[str]:
    """
    Produces permutations with chars replaced by chars in :attr:`aff.TRY <spylls.hunspell.data.aff.Aff.TRY>`
    set.
    """

    if not trystring:
        return

    for c in trystring:
        for i in reversed(range(0, len(word))):
            if word[i] == c:
                continue
            yield word[:i] + c + word[i+1:]


def doubletwochars(word: str) -> Iterator[str]:
    """
    Produces permutations with accidental two-letter-doubling fixed (vacation -> vacacation)
    """

    if len(word) < 5:
        return

    # TODO: 1) for vacacation yields "vacation" twice, hunspell's algo kinda wiser
    # 2) maybe just use regexp?..
    for i in range(2, len(word)):
        if word[i-2] == word[i] and word[i-3] == word[i-1]:
            yield word[:i-1] + word[i+1:]


def twowords(word: str) -> Iterator[List[str]]:
    """
    Produces permutation of splitting in two words in all possible positions.
    """

    for i in range(1, len(word)):
        yield [word[:i], word[i:]]
