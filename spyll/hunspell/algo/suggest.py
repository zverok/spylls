from itertools import chain, product, islice
from typing import Iterator, Tuple

from spyll.hunspell.algo import ngram_suggest, permutations as pmt, capitalization as cap


class Observed:
    def __init__(self):
        self.seen = []

    def __call__(self, generator):
        for item in generator:
            self.seen.append(item)
            yield item


def suggest(dic, word: str) -> Iterator[str]:
    yield from (sug for sug, _ in suggest_debug(dic, word))


def suggest_debug(dic, word: str) -> Iterator[Tuple[str, str]]:
    good = Observed()
    very_good = Observed()
    seen = set()

    def oconv(word):
        if not dic.aff.OCONV:
            return word
        for src, dst in dic.aff.OCONV:
            word = word.replace(src, dst)
        return word

    def handle_found(suggestion, source, *, ignore_included=False):
        if dic.keepcase(suggestion) and not dic.aff.CHECKSHARPS:
            cased_suggestion = suggestion
        else:
            cased_suggestion = cap.coerce(suggestion, captype)
            if suggestion != cased_suggestion and dic.is_forbidden(cased_suggestion):
                cased_suggestion = suggestion
        if dic.is_forbidden(cased_suggestion):
            return
        if ignore_included and any(s in cased_suggestion for s in seen) or cased_suggestion in seen:
            return

        seen.add(cased_suggestion)
        yield oconv(cased_suggestion), source

    captype, variants = cap.variants(word)

    if dic.aff.CHECKSHARPS and 'ß' in word and cap.guess(word.replace('ß', '')) == cap.Cap.ALL:
        captype = cap.Cap.ALL

    if dic.aff.FORCEUCASE:
        if checkword(dic, word.capitalize()):
            yield from handle_found(word.capitalize(), 'forcecase')
            return # No more need to check anything

    for variant in variants[1:]:
        if checkword(dic, variant):
            yield from handle_found(variant, 'case')

    for variant in variants:
        for sug, source in good_permutations(dic, variant):
            yield from good(handle_found(sug, source))

    for variant in variants:
        for sug, source in very_good_permutations(dic, variant):
            yield from very_good(handle_found(sug, source))

    if very_good.seen:
        return

    for variant in variants:
        for sug, source in questionable_permutations(dic, variant):
            yield from handle_found(sug, source)

    if very_good.seen or good.seen or dic.aff.MAXNGRAMSUGS == 0:
        return

    ngramsugs = 0
    for sug in ngram_suggest.ngram_suggest(
                dic, word.lower(), maxdiff=dic.aff.MAXDIFF, onlymaxdiff=dic.aff.ONLYMAXDIFF):
        yield from islice(handle_found(sug, 'ngram', ignore_included=True), dic.aff.MAXNGRAMSUGS)


def checkword(dic, word, *, with_compounds=None, **kwarg):
    return dic.lookup(word, capitalization=False, allow_nosuggest=False, with_compounds=with_compounds, **kwarg)


def very_good_permutations(dic, word: str) -> Iterator[str]:
    for sug in pmt.twowords(word):
        if checkword(dic, ' '.join(sug)):
            yield ' '.join(sug), 'spaceword'
        if dic.aff.use_dash() and checkword(dic, '-'.join(sug), allow_break=False):
            yield '-'.join(sug), 'spaceword'


def good_permutations(dic, word: str) -> Iterator[str]:
    # suggestions for an uppercase word (html -> HTML)
    if checkword(dic, word.upper()):
        yield (word.upper(), 'uppercase')

    # typical fault of spelling
    for sug, source in product(pmt.replchars(word, dic.aff.REP), ['replchars']):
        if type(sug) is list:
            # could've come from replchars + spaces -- but no "-"-checks here
            if all(checkword(dic, s) for s in sug):
                yield ' '.join(sug), source
        elif type(sug) is str:
            if checkword(dic, sug):
                yield sug, source


def questionable_permutations(dic, word: str) -> Iterator[str]:
    iterator = chain(
        # wrong char from a related set
        product(pmt.mapchars(word, dic.aff.MAP), ['mapchars']),
        # swap the order of chars by mistake
        product(pmt.swapchar(word), ['swapchar']),
        # swap the order of non adjacent chars by mistake
        product(pmt.longswapchar(word), ['longswapchar']),
        # hit the wrong key in place of a good char (case and keyboard)
        product(pmt.badcharkey(word, dic.aff.KEY), ['badcharkey']),
        # add a char that should not be there
        product(pmt.extrachar(word), ['extrachar']),
        # forgot a char
        product(pmt.forgotchar(word, dic.aff.TRY), ['forgotchar']),
        # move a char
        product(pmt.movechar(word), ['movechar']),
        # just hit the wrong key in place of a good char
        product(pmt.badchar(word, dic.aff.TRY), ['badchar']),
        # double two characters
        product(pmt.doubletwochars(word), ['doubletwochars']),

        # perhaps we forgot to hit space and two words ran together
        product(pmt.twowords(word), ['twowords'])
    )

    for sug, source in iterator:
        if type(sug) is list:
            # FIXME: this is how it is in hunspell (see opentaal_forbiddenword1): either BOTH
            # should be compound, or BOTH should be not. I am not sure it is the right thing
            # to do, but just want to catch up with tests, for now.
            # if all(checkword(dic, s, with_compounds=False, allow_break=False) for s in sug) or \
            #    all(checkword(dic, s, with_compounds=True, allow_break=False) for s in sug):
            #     yield ' '.join(sug), source
            #     if dic.aff.use_dash():
            #         yield '-'.join(sug), source
            if all(checkword(dic, s, allow_break=False) for s in sug):
                yield ' '.join(sug), source
                if dic.aff.use_dash():
                    yield '-'.join(sug), source
        elif type(sug) is str:
            if checkword(dic, sug):
                yield sug, source
