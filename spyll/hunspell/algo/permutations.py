import re
import itertools

from typing import Iterator, Union, List, Tuple, Set

from spyll.hunspell import data


MAX_CHAR_DISTANCE = 4


def permutations(word: str, aff: data.Aff) -> Iterator[Union[str, Tuple[str, str]]]:
    return itertools.chain(
        [word],                      # source word itself is also a valid permutation
        [word.upper()],              # suggestions for an uppercase word (html -> HTML)
        replchars(word, aff.rep),    # typical fault of spelling
        mapchars(word, aff.map),     # wrong char from a related set
        swapchar(word),              # swap the order of chars by mistake
        longswapchar(word),          # swap the order of non adjacent chars by mistake
        badcharkey(word, aff.key),   # hit the wrong key in place of a good char (case and keyboard)
        extrachar(word),             # add a char that should not be there
        forgotchar(word, aff.try_),  # forgot a char
        movechar(word),              # move a char
        badchar(word, aff.try_),     # just hit the wrong key in place of a good char
        doubletwochars(word),        # double two characters

        # perhaps we forgot to hit space and two words ran together
        # (dictionary word pairs have top priority here, so
        # we always suggest them, in despite of nosplitsugs, and
        # drop compound word and other suggestions)
        twowords(word)
    )


# suggestions for a typical fault of spelling, that
# differs with more than 1 letter from the right form.
#
# uses .aff's file REP table
def replchars(word: str, reptable: List[Tuple[str, str]]) -> Iterator[Union[str, Tuple[str, str]]]:
    if len(word) < 2 or not reptable:
        return

    for (pattern, replacement) in reptable:
        # TODO: compiled at aff loading
        for match in re.compile(pattern).finditer(word):
            suggestion = word[:match.start()] + replacement.replace('_', ' ') + word[match.end():]
            yield suggestion
            if ' ' in suggestion:
                yield suggestion.split(' ', 2)


# suggestions for when chose the wrong char out of a related set
#
# uses aff.map -- list of sets of potentially similar chars
def mapchars(word: str, maptable: List[Set[str]]) -> Iterator[str]:
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


# error is adjacent letter were swapped
def swapchar(word: str) -> Iterator[str]:
    if len(word) < 2:
        return

    for i in range(0, len(word) - 1):
        yield word[:i] + word[i+1] + word[i+1] + word[i+2:]

    # try double swaps for short words
    # ahev -> have, owudl -> would
    if 4 <= len(word) <= 5:
        yield word[1] + word[0] + (word[2] if len(word) == 5 else '') + word[-1] + word[-2]
        if len(word) == 5:
            yield word[0] + word[2] + word[1] + word[-1] + word[-2]


# error is not adjacent letter were swapped
def longswapchar(word: str) -> Iterator[str]:
    for first in range(0, len(word) - 2):
        for second in range(first + 2, min(first + MAX_CHAR_DISTANCE, len(word))):
            yield word[:first] + word[second] + word[first+1:second] + word[first] + word[second+1:]


# error is wrong char in place of correct one (case and keyboard related version)
def badcharkey(word: str, layout: str) -> Iterator[str]:
    for i in range(0, len(word)):
        c = word[i]
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


# error is word has an extra letter it does not need
def extrachar(word: str) -> Iterator[str]:
    if len(word) < 2:
        return

    for i in range(0, len(word)):
        yield word[:i] + word[i+1:]


# error is missing a letter it needs
# uses aff.try -- if it is absent, doesn't try anything!
def forgotchar(word, trystring):
    if not trystring:
        return

    for c in trystring:
        for i in range(0, len(word)):
            yield word[:i] + c + word[i:]


# error is a letter was moved
def movechar(word: str) -> Iterator[str]:
    if len(word) < 2:
        return

    for frompos in range(0, len(word)):
        for topos in range(frompos + 3, min(len(word), frompos + MAX_CHAR_DISTANCE + 1)):
            yield word[:frompos] + word[frompos+1:topos] + word[frompos] + word[topos:]

    for frompos in reversed(range(0, len(word))):
        for topos in reversed(range(max(0, frompos - MAX_CHAR_DISTANCE + 1), frompos - 1)):
            yield word[:topos] + word[frompos] + word[topos:frompos] + word[frompos+1:]


# error is wrong char in place of correct one
def badchar(word: str, trystring: str) -> Iterator[str]:
    if not trystring:
        return

    for c in trystring:
        for i in reversed(range(0, len(word))):
            if word[i] == c:
                continue
            yield word[:i] + c + word[i+1:]


# perhaps we doubled two characters
# (for example vacation -> vacacation)
# The recognized pattern with regex back-references:
# "(.)(.)\1\2\1" or "..(.)(.)\1\2"
def doubletwochars(word: str) -> Iterator[str]:
    if len(word) < 5:
        return

    # TODO: 1) for vacacation yields "vacation" twice, hunspell's algo kinda wiser
    # 2) maybe just use regexp?..
    for i in range(2, len(word)):
        if word[i-2] == word[i] and word[i-3] == word[i-1]:
            yield word[:i-1] + word[i+1:]


# error is should have been two words
# return value is true, if there is a dictionary word pair,
# or there was already a good suggestion before calling
# this function.
def twowords(word: str) -> Iterator[Tuple[str, str]]:
    for i in range(1, len(word)):
        yield [word[:i], word[i:]]
