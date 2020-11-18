from typing import Iterator, Union, List, Set

from spyll.hunspell.data import aff


MAX_CHAR_DISTANCE = 4


def replchars(word: str, reptable: List[aff.RepPattern]) -> Iterator[Union[str, List[str]]]:
    """
    suggestions for a typical fault of spelling, that
    differs with more than 1 letter from the right form.

    uses :attr:`aff.REP <spyll.hunspell.data.aff.Aff.REP>` table
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
    Suggestions for when chose the wrong char out of a related set

    Uses :attr:`aff.MAP <spyll.hunspell.data.aff.Aff.MAP>` -- list of sets of potentially similar chars
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
    """error is adjacent letter were swapped"""

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
    """error is not adjacent letter were swapped"""

    for first in range(0, len(word) - 2):
        for second in range(first + 2, min(first + MAX_CHAR_DISTANCE, len(word))):
            yield word[:first] + word[second] + word[first+1:second] + word[first] + word[second+1:]


def badcharkey(word: str, layout: str) -> Iterator[str]:
    """error is wrong char in place of correct one (case and keyboard related version)"""

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
    """error is word has an extra letter it does not need"""
    if len(word) < 2:
        return

    for i in range(0, len(word)):
        yield word[:i] + word[i+1:]


def forgotchar(word: str, trystring: str) -> Iterator[str]:
    """
    error is missing a letter it needs

    uses :attr:`aff.TRY <spyll.hunspell.data.aff.Aff.TRY>` -- if it is absent, doesn't try anything!
    """

    if not trystring:
        return

    for c in trystring:
        for i in range(0, len(word)):
            yield word[:i] + c + word[i:]


def movechar(word: str) -> Iterator[str]:
    """
    error is a letter was moved
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
    error is wrong char in place of correct one

    uses :attr:`aff.TRY <spyll.hunspell.data.aff.Aff.TRY>` -- if it is absent, doesn't try anything!
    """

    if not trystring:
        return

    for c in trystring:
        for i in reversed(range(0, len(word))):
            if word[i] == c:
                continue
            yield word[:i] + c + word[i+1:]


def doubletwochars(word: str) -> Iterator[str]:
    r"""
    perhaps we doubled two characters
    (for example vacation -> vacacation)
    The recognized pattern with regex back-references: ``"(.)(.)\1\2\1"`` or ``"..(.)(.)\1\2"``
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
    error is should have been two words
    """

    for i in range(1, len(word)):
        yield [word[:i], word[i:]]
