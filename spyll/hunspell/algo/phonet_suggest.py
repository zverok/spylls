from __future__ import annotations

from typing import Iterator, List, Tuple
from operator import itemgetter
import heapq

from spyll.hunspell.data import phonet

import spyll.hunspell.algo.string_metrics as sm
import spyll.hunspell.algo.ngram_suggest as ng

MAX_ROOTS = 100


def phonet_suggest(word: str, *, dictionary_words: List[data.dic.Word], table: phonet.Table) -> Iterator[str]:
    word = word.lower()
    word_ph = metaphone(table, word)

    scores: List[Tuple[float, str]] = []

    # NB: This cycle is repeated from ngram_suggest when both are used.
    # But it is MUCH easier to understand and test this way.
    for dword in dictionary_words:
        if abs(len(dword.stem) - len(word)) > 4:
            continue
        # TODO: more exceptions

        nscore = ng.root_score(word, dword.stem)
        if dword.alt_spellings:
            for variant in dword.alt_spellings:
                nscore = max(nscore, ng.root_score(word, variant))

        if nscore > 2 and abs(len(word) - len(dword.stem)) <= 3:
            score = 2 * sm.ngram(3, word_ph, metaphone(table, dword.stem), longer_worse=True)
            if len(scores) > MAX_ROOTS:
                heapq.heappushpop(scores, (score, dword.stem))
            else:
                heapq.heappush(scores, (score, dword.stem))

    guesses = heapq.nlargest(MAX_ROOTS, scores)

    guesses2 = [(score + detailed_score(word, dword.lower()), dword) for (score, dword) in guesses]
    # (NB: actually, we might not need ``key`` here, but it is
    # added for sorting stability; doesn't changes the objective quality of suggestions, but passes
    # hunspell test ``phone.sug``!)
    guesses2 = sorted(guesses2, key=itemgetter(0), reverse=True)

    for (_, sug) in guesses2:
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
