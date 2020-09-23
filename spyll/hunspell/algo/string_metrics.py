from enum import Enum
from typing import List, Optional, Tuple, cast

LCS = Enum('LCS', 'UP LEFT UPLEFT')


def commoncharacterpositions(s1: str, s2: str) -> Tuple[int, bool]:
    num = 0
    diffpos = []

    for (i, (c1, c2)) in enumerate(zip(s1, s2)):
        if c1 == c2:
            num += 1
        else:
            diffpos.append(i)

    if len(diffpos) == 2:   # two string differ only by exactly two chars swaped
        p1, p2 = diffpos    # pylint: disable=unbalanced-tuple-unpacking
        swap = len(s1) == len(s2) and s1[p1] == s2[p2] and s1[p2] == s2[p1]
    else:
        swap = False

    return (num, swap)


def leftcommonsubstring(s1: str, s2: str) -> float:
    for (i, (c1, c2)) in enumerate(zip(s1, s2)):
        if c1 != c2:
            return i

    return min(len(s1), len(s2))


def ngram(n: int, s1: str, s2: str, *,
          weighted=False, any_mismatch=False, longer_worse=False) -> float:

    l2 = len(s2)
    if l2 == 0:
        return 0
    l1 = len(s1)

    nscore = 0
    for j in range(1, n + 1):
        ns = 0
        for i in range(l1 - j + 1):
            if s1[i:i+j] in s2:
                ns += 1
            elif weighted:
                ns -= 1
                if i in (0, l1 - j):
                    ns -= 1  # side weight
        nscore += ns
        if ns < 2 and not weighted:
            break

    ns = 0
    if longer_worse:
        ns = (l2 - l1) - 2
    if any_mismatch:
        ns = abs(l2 - l1) - 2

    return nscore - ns if ns > 0 else nscore


def lcslen(s1: str, s2: str) -> int:
    result = lcs(s1, s2)
    if not result:
        return 0

    i = len(s1)
    j = n = len(s2)

    res = 0
    while (i != 0) and (j != 0):
        if result[i * (n + 1) + j] == LCS.UPLEFT:
            res += 1
            i -= 1
            j -= 1
        elif result[i * (n + 1) + j] == LCS.UP:
            i -= 1
        else:
            j -= 1

    return res


def lcs(s1: str, s2: str) -> List[Optional[LCS]]:
    m = len(s1)
    n = len(s2)

    c: List[Optional[int]] = [None] * ((m + 1) * (n + 1))
    b: List[Optional[LCS]] = [None] * ((m + 1) * (n + 1))

    for i in range(m+1):
        c[i * (n + 1)] = 0
    for j in range(n+1):
        c[j] = 0

    for i in range(1, m+1):
        for j in range(1, n+1):
            if s1[i - 1] == s2[j - 1]:
                c[i * (n + 1) + j] = cast(int, c[(i - 1) * (n + 1) + j - 1]) + 1
                b[i * (n + 1) + j] = LCS.UPLEFT
            elif cast(int, c[(i - 1) * (n + 1) + j]) >= cast(int, c[i * (n + 1) + j - 1]):
                c[i * (n + 1) + j] = c[(i - 1) * (n + 1) + j]
                b[i * (n + 1) + j] = LCS.UP
            else:
                c[i * (n + 1) + j] = c[i * (n + 1) + j - 1]
                b[i * (n + 1) + j] = LCS.LEFT

    return b
