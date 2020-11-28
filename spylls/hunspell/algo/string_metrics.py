from typing import Tuple


def commoncharacterpositions(s1: str, s2: str) -> Tuple[int, bool]:
    """
    Number of occurences of the exactly same characters in exactly same position.
    Returns also boolean flag if the only difference in characters of two strings is exactly one
    swap ("paris" => "piras") -- both values are used in the same place of
    :meth:`ngram_suggest.precise_affix_score <spylls.hunspell.algo.ngram_suggest.precise_affix_score>`
    """

    num = 0
    diffpos = []

    for (i, (c1, c2)) in enumerate(zip(s1, s2)):
        if c1 == c2:
            num += 1
        else:
            diffpos.append(i)

    if len(diffpos) == 2:   # two string differ only by exactly two chars swaped
        p1, p2 = diffpos    # pylint: disable=unbalanced-tuple-unpacking
        is_swap = len(s1) == len(s2) and s1[p1] == s2[p2] and s1[p2] == s2[p1]
    else:
        is_swap = False

    return (num, is_swap)


def leftcommonsubstring(s1: str, s2: str) -> int:
    """Size of the common start of two strings. "foo", "bar" => 0, "built", "build" => 4, "cat", "cats" => 3"""
    for (i, (c1, c2)) in enumerate(zip(s1, s2)):
        if c1 != c2:
            return i

    return min(len(s1), len(s2))


def ngram(max_ngram_size: int, s1: str, s2: str, *,
          weighted: bool = False, any_mismatch: bool = False, longer_worse: bool = False) -> int:

    """
    Calculates how many of n-grams of s1 are contained in s2 (the more the number, the more words
    are similar).

    Args:
      max_ngram_size: n in ngram
      s1: string to compare
      s2: string to compare
      weighted: substract from result for ngrams *not* contained
      longer_worse: add a penalty when second string is longer
      any_mismatch: add a penalty for any string lengtht difference

    FIXME: Actually, the last two settings do NOT participate in ngram counting by themselves, they
    are just adjusting the final score, but that's how it was structured in Hunspell.
    """

    l2 = len(s2)
    if l2 == 0:
        return 0
    l1 = len(s1)

    nscore = 0
    # For all sizes of ngram up to desired...
    for ngram_size in range(1, max_ngram_size + 1):
        ns = 0
        # Check every position in the first string
        for pos in range(l1 - ngram_size + 1):
            # ...and if the ngram of current size in this position is present in ANY place in second string
            if s1[pos:pos+ngram_size] in s2:
                # increase score
                ns += 1
            elif weighted:
                # For "weighted" ngrams, decrease score if ngram is not found,
                ns -= 1
                if pos == 0 or pos + ngram_size == l1:
                    # ...and decrease once more if it was the beginning or end of first string
                    ns -= 1
        nscore += ns
        if ns < 2 and not weighted:
            break

    # longer_worse setting adds a penalty if the second string is longer than first
    if longer_worse:
        penalty = (l2 - l1) - 2
    # any_mismatch adds a penalty for _any_ string length difference
    elif any_mismatch:
        penalty = abs(l2 - l1) - 2
    else:
        penalty = 0

    return nscore - penalty if penalty > 0 else nscore


def lcslen(s1: str, s2: str) -> int:
    """
    Classic "LCS (longest common subsequence) length" algorithm.
    This implementation is stolen shamelessly from https://gist.github.com/cgt/c0c47c100efda1d11854
    """

    m = len(s1)
    n = len(s2)

    c = [[0 for j in range(n+1)] for i in range(m+1)]

    for i in range(0, m):
        for j in range(0, n):
            if s1[i] == s2[j]:
                c[i][j] = c[i-1][j-1] + 1
            elif c[i-1][j] >= c[i][j-1]:
                c[i][j] = c[i-1][j]
            else:
                c[i][j] = c[i][j-1]

    return c[m-1][n-1]
