from itertools import chain, product
from typing import Iterator, Set, Union, Tuple, cast

from spyll.hunspell.algo import ngram_suggest, permutations as pmt, capitalization as cap

def suggest(dic, word: str) -> Iterator[str]:
    for sug, _ in suggest_debug(dic, word):
        yield sug

def suggest_debug(dic, word: str) -> Iterator[Tuple[str, str]]:
    good = False
    very_good = False
    seen = set()

    captype, variants = cap.variants(word)

    def handle_found(suggestion, *, ignore_included=False):
        cased_suggestion = cap.coerce(suggestion, captype)
        if suggestion != cased_suggestion and dic.is_forbidden(cased_suggestion):
            cased_suggestion = suggestion
        if dic.is_forbidden(cased_suggestion):
            return None
        if ignore_included and any(s in cased_suggestion for s in seen) or cased_suggestion in seen:
            return None

        seen.add(cased_suggestion)
        return cased_suggestion

    for variant in variants[1:]:
        if dic.lookup_nocap(variant):
            sug = handle_found(variant)
            if sug:
                yield sug, 'case'

    for variant in variants:
        for sug, source in good_permutations(dic, variant):
            sug = handle_found(sug)
            if sug:
                good = True
                yield sug, source

    for variant in variants:
        for sug, source in very_good_permutations(dic, variant):
            sug = handle_found(sug)
            if sug:
                very_good = True
                yield sug, source

    if very_good:
        return

    for variant in variants:
        for sug, source in questionable_permutations(dic, variant):
            sug = handle_found(sug)
            if sug:
                found = True
                yield sug, source

    if very_good or good or dic.aff.maxngramsugs == 0:
        return

    ngramsugs = 0
    for sug in ngram_suggest.ngram_suggest(
                dic, word.lower(), maxdiff=dic.aff.maxdiff, onlymaxdiff=dic.aff.onlymaxdiff):
        sug = handle_found(sug, ignore_included=True)
        if sug:
            yield sug, 'ngram'
        ngramsugs += 1
        if ngramsugs >= dic.aff.maxngramsugs:
            break

def very_good_permutations(dic, word: str) -> Iterator[str]:
    for sug in pmt.twowords(word):
        if dic.lookup_nocap(' '.join(sug)):
            yield ' '.join(sug), 'spaceword'
        if dic.aff.use_dash() and dic.lookup_nocap('-'.join(sug)):
            yield '-'.join(sug), 'spaceword'

def good_permutations(dic, word: str) -> Iterator[str]:
    iterator = chain(
        # suggestions for an uppercase word (html -> HTML)
        [(word.upper(), 'uppercase')],
        # typical fault of spelling
        product(pmt.replchars(word, dic.aff.rep), ['replchars'])
    )

    for sug, source in iterator:
        if type(sug) is list:
            # could've come from replchars + spaces -- but no "-"-checks here
            if all(dic.lookup_nocap(s) for s in sug):
                yield ' '.join(sug), source
        elif type(sug) is str:
            if dic.lookup_nocap(sug):
                yield sug, source

def questionable_permutations(dic, word: str) -> Iterator[str]:
    iterator = chain(
        # wrong char from a related set
        product(pmt.mapchars(word, dic.aff.map), ['mapchars']),
        # swap the order of chars by mistake
        product(pmt.swapchar(word), ['swapchar']),
        # swap the order of non adjacent chars by mistake
        product(pmt.longswapchar(word), ['longswapchar']),
        # hit the wrong key in place of a good char (case and keyboard)
        product(pmt.badcharkey(word, dic.aff.key), ['badcharkey']),
        # add a char that should not be there
        product(pmt.extrachar(word), ['extrachar']),
        # forgot a char
        product(pmt.forgotchar(word, dic.aff.try_), ['forgotchar']),
        # move a char
        product(pmt.movechar(word), ['movechar']),
        # just hit the wrong key in place of a good char
        product(pmt.badchar(word, dic.aff.try_), ['badchar']),
        # double two characters
        product(pmt.doubletwochars(word), ['doubletwochars']),

        # perhaps we forgot to hit space and two words ran together
        product(pmt.twowords(word), ['twowords'])
    )

    for sug, source in iterator:
        if type(sug) is list:
            if all(dic.lookup_nocap(s) for s in sug):
                yield ' '.join(sug), source
                if dic.aff.use_dash():
                    yield '-'.join(sug), source
        elif type(sug) is str:
            if dic.lookup_nocap(sug):
                yield sug, source
