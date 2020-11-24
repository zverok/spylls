from __future__ import annotations

from typing import Iterator, List, Tuple
from operator import itemgetter
import heapq

from spyll.hunspell.data import aff, dic

import spyll.hunspell.algo.string_metrics as sm
import spyll.hunspell.algo.ngram_suggest as ng

MAX_ROOTS = 100


def phonet_suggest(misspelling: str, *, dictionary_words: List[dic.Word], table: aff.PhonetTable) -> Iterator[str]:
    """
    Phonetical suggestion algorithm provides suggestions based on phonetial (prononication) similarity.
    It requires ``*.aff``-file to define :attr:`PHONE <spyll.hunspell.data.aff.Aff.PHONE>` table --
    which, we should add, is *extremely* rare in known dictionaries.
    """

    misspelling = misspelling.lower()
    misspelling_ph = metaphone(table, misspelling)

    scores: List[Tuple[float, str]] = []

    # First, select words from dictionary whose stems alike the misspelling we are trying to suggest.
    #
    # This cycle is exactly the same as the first cycle in ngram_suggest. In fact, in original Hunspell
    # both ngram and phonetical suggestion are done in one pass inside ngram_suggest, which is
    # more effective (one iteration through whole dictionary instead of two) but much harder to
    # understand and debug.
    #
    # Considering extreme rarity of metaphone-enabled dictionaries, and "educational" goal of
    # spyll, we split it out.
    for word in dictionary_words:
        if abs(len(word.stem) - len(misspelling)) > 3:
            continue

        # First, we calculate "regular" similarity score, just like in ngram_suggest
        nscore = ng.root_score(misspelling, word.stem)

        if word.alt_spellings:
            for variant in word.alt_spellings:
                nscore = max(nscore, ng.root_score(misspelling, variant))

        if nscore <= 2:
            continue

        # ...and if it shows words are somewhat close, we calculate metaphone score
        score = 2 * sm.ngram(3, misspelling_ph, metaphone(table, word.stem), longer_worse=True)

        if len(scores) > MAX_ROOTS:
            heapq.heappushpop(scores, (score, word.stem))
        else:
            heapq.heappush(scores, (score, word.stem))

    guesses = heapq.nlargest(MAX_ROOTS, scores)

    # Finally, we sort suggestions by simplistic string similarity metric (of the misspelling and
    # dictionary word's stem)
    guesses2 = [(score + detailed_score(misspelling, word.lower()), word) for (score, word) in guesses]
    # (NB: actually, we might not need ``key`` here, but it is
    # added for sorting stability; doesn't changes the objective quality of suggestions, but passes
    # hunspell test ``phone.sug``!)
    guesses2 = sorted(guesses2, key=itemgetter(0), reverse=True)

    for (_, sug) in guesses2:
        yield sug


def detailed_score(word1: str, word2: str) -> float:
    return 2 * sm.lcslen(word1, word2) - abs(len(word1) - len(word2)) + sm.leftcommonsubstring(word1, word2)


def metaphone(table: aff.PhonetTable, word: str) -> str:
    """
    Metaphone calculation
    """

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
