from __future__ import annotations

from typing import Iterator
from operator import itemgetter

from spyll.hunspell.data import phonet

import spyll.hunspell.algo.string_metrics as sm
from spyll.hunspell.algo.util import ScoredArray
import spyll.hunspell.algo.ngram_suggest as ng

MAX_ROOTS = 100


def phonet_suggest(word: str, *, roots, table: phonet.Table) -> Iterator[str]:
    word = word.lower()
    word_ph = metaphone(table, word)

    scores = ScoredArray[str](MAX_ROOTS)

    # NB: This cycle is repeated from ngram_suggest when both are used.
    # But it is MUCH easier to understand and test this way.
    for dword in roots:
        if abs(len(dword.stem) - len(word)) > 4:
            continue
        # TODO: more exceptions

        nscore = ng.root_score(word, dword.stem)
        if dword.phonetic():
            for variant in dword.phonetic():
                nscore = max(nscore, ng.root_score(word, variant))

        if nscore > 2 and abs(len(word) - len(dword.stem)) <= 3:
            score = 2 * sm.ngram(3, word_ph, metaphone(table, dword.stem), longer_worse=True)
            scores.push(dword.stem, score)

    guesses = sorted(scores.result(), key=itemgetter(1), reverse=True)

    # TODO: Use aff.MAXPHONSUGS setting
    guesses2 = [(dword, score + detailed_score(word, dword.lower())) for (dword, score) in guesses]
    guesses2 = sorted(guesses2, key=itemgetter(1), reverse=True)
    for (sug, _) in guesses2:
        yield sug


def detailed_score(word1: str, word2: str) -> float:
    return 2 * sm.lcslen(word1, word2) - abs(len(word1) - len(word2)) + sm.leftcommonsubstring(word1, word2)


def metaphone(table, word):
    # for each position in word:
    # find rules that match (^ -- only once, $ -- fullmatch)
    # "-" -- make them lookahead

    pos = 0
    word = word.upper()
    res = ''
    while pos < len(word):
        match = None
        for rule in table.rules[word[pos]]:
            match = rule.match(word, pos)
            if match:
                res += rule.replacement
                pos += match.span()[1] - match.span()[0]
                break
        if not match:
            pos += 1
    return res
