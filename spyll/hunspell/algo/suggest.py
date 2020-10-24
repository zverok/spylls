from typing import Iterator, List, Set, Union

import dataclasses
from dataclasses import dataclass

from spyll.hunspell import data
from spyll.hunspell.data.aff import RepPattern
from spyll.hunspell.algo import ngram_suggest, phonet, permutations as pmt

MAXPHONSUGS = 2


@dataclass
class Suggestion:
    text: str
    source: str

    allow_break: bool = True

    def __repr__(self):
        return f"Suggestion[{self.source}]({self.text})"

    def replace(self, **changes):
        return dataclasses.replace(self, **changes)


@dataclass
class MultiWordSuggestion:
    words: List[str]
    source: str

    allow_dash: bool = True

    def stringify(self, separator=' '):
        return Suggestion(separator.join(self.words), self.source)

    def __repr__(self):
        return f"Suggestion[{self.source}]({self.words!r})"


class Suggest:
    def __init__(self, aff: data.Aff, dic: data.Dic, lookup):
        self.aff = aff
        self.dic = dic
        self.lookup = lookup
        # TODO: there also could be "pretty ph:prity ph:priti->pretti", "pretty ph:prity*"
        # TODO: if (captype==INITCAP)
        self.replacements = [
            # FIXME: Shouldn't work, probably...
            RepPattern(phonetic, word.stem)
            for word in dic.words if word.phonetic()
            for phonetic in word.phonetic()
        ]
        # print(self.replacements)

    def __call__(self, word: str) -> Iterator[str]:
        yield from (suggestion.text for suggestion in self.suggest_debug(word))

    def suggest_debug(self, word: str) -> Iterator[Suggestion]:
        def oconv(word):
            return self.aff.OCONV(word) if self.aff.OCONV else word

        def check_suggestion(word, **kwarg):
            return self.lookup(word, capitalization=False, allow_nosuggest=False, **kwarg)

        def filter_suggestions(suggestions):
            for suggestion in suggestions:
                if isinstance(suggestion, MultiWordSuggestion):
                    if all(check_suggestion(word, allow_break=False) for word in suggestion.words):
                        yield suggestion.stringify()
                        if suggestion.allow_dash:
                            yield suggestion.stringify('-')
                else:
                    if check_suggestion(suggestion.text, allow_break=suggestion.allow_break):
                        yield suggestion

        def keep_case(word):
            return self.aff.KEEPCASE and self.dic.has_flag(word, self.aff.KEEPCASE)

        def is_forbidden(word):
            return self.aff.FORBIDDENWORD and self.dic.has_flag(word, self.aff.FORBIDDENWORD)

        handled: Set[str] = set()

        def handle_found(suggestion, *, ignore_included=False):
            text = suggestion.text
            if keep_case(text) and not self.aff.CHECKSHARPS:
                # Don't change text
                pass
            else:
                text = self.aff.collation.coerce(text, captype)
                if text != suggestion.text and is_forbidden(text):
                    text = suggestion.text
            if is_forbidden(text):
                return
            if text in handled or ignore_included and any(previous in text for previous in handled):
                return

            handled.add(text)
            yield suggestion.replace(text=oconv(text))

        captype, variants = self.aff.collation.corrections(word)

        # if self.aff.CHECKSHARPS and 'ß' in word and cap.guess(word.replace('ß', '')) == cap.Cap.ALL:
        #     captype = cap.Cap.ALL

        good = False
        very_good = False

        if self.aff.FORCEUCASE:
            if check_suggestion(word.capitalize()):
                yield from handle_found(Suggestion(word.capitalize(), 'forcecase'))
                return  # No more need to check anything

        for idx, variant in enumerate(variants):
            if idx > 0 and check_suggestion(variant):
                yield from handle_found(Suggestion(variant, 'case'))

            for suggestion in filter_suggestions(self.good_permutations(variant)):
                for res in handle_found(suggestion):
                    good = True
                    yield res

            for suggestion in filter_suggestions(self.very_good_permutations(variant)):
                for res in handle_found(suggestion):
                    very_good = True
                    yield res

            if very_good:
                return

            for suggestion in filter_suggestions(self.questionable_permutations(variant)):
                yield from handle_found(suggestion)

        if very_good or good or self.aff.MAXNGRAMSUGS == 0:
            return

        ngrams_seen = 0
        for sug in self.ngram_suggestions(word):
            for res in handle_found(Suggestion(sug, 'ngram'), ignore_included=True):
                ngrams_seen += 1
                yield res
            if ngrams_seen >= self.aff.MAXNGRAMSUGS:
                break

        phonet_seen = 0
        for sug in self.phonet_suggestions(word):
            for res in handle_found(Suggestion(sug, 'phonet'), ignore_included=True):
                phonet_seen += 1
                yield res
            if phonet_seen >= MAXPHONSUGS:
                break

    def very_good_permutations(self, word: str) -> Iterator[Suggestion]:
        for words in pmt.twowords(word):
            yield Suggestion(' '.join(words), 'spaceword')

            if self.aff.use_dash():
                yield Suggestion('-'.join(words), 'spaceword', allow_break=False)

    def good_permutations(self, word: str) -> Iterator[Union[Suggestion, MultiWordSuggestion]]:
        # suggestions for an uppercase word (html -> HTML)
        yield Suggestion(word.upper(), 'uppercase')

        # typical fault of spelling, might return several words if REP table has "REP <something> _",
        # ...in this case we should suggest both "<word1> <word2>" as one dictionary entry, and
        # "<word1>" "<word1>" as a sequence -- but clarifying this sequence might NOT be joined by "-"
        for suggestion in pmt.replchars(word, self.aff.REP):
            if isinstance(suggestion, list):
                yield Suggestion(' '.join(suggestion), 'replchars')
                yield MultiWordSuggestion(suggestion, 'replchars', allow_dash=False)
            else:
                yield Suggestion(suggestion, 'replchars')

        for suggestion in pmt.replchars(word, self.replacements):
            if isinstance(suggestion, list):
                yield MultiWordSuggestion(suggestion, 'replchars/ph', allow_dash=False)
            else:
                yield Suggestion(suggestion, 'replchars/ph')

    def questionable_permutations(self, word: str) -> Iterator[Union[Suggestion, MultiWordSuggestion]]:
        # wrong char from a related set
        for suggestion in pmt.mapchars(word, self.aff.MAP):
            yield Suggestion(suggestion, 'mapchars')

        # swap the order of chars by mistake
        for suggestion in pmt.swapchar(word):
            yield Suggestion(suggestion, 'swapchar')

        # swap the order of non adjacent chars by mistake
        for suggestion in pmt.longswapchar(word):
            yield Suggestion(suggestion, 'longswapchar')

        # hit the wrong key in place of a good char (case and keyboard)
        for suggestion in pmt.badcharkey(word, self.aff.KEY):
            yield Suggestion(suggestion, 'badcharkey')

        # add a char that should not be there
        for suggestion in pmt.extrachar(word):
            yield Suggestion(suggestion, 'extrachar')

        # forgot a char
        for suggestion in pmt.forgotchar(word, self.aff.TRY):
            yield Suggestion(suggestion, 'forgotchar')

        # move a char
        for suggestion in pmt.movechar(word):
            yield Suggestion(suggestion, 'movechar')

        # just hit the wrong key in place of a good char
        for suggestion in pmt.badchar(word, self.aff.TRY):
            yield Suggestion(suggestion, 'badchar')

        # double two characters
        for suggestion in pmt.doubletwochars(word):
            yield Suggestion(suggestion, 'doubletwochars')

        # perhaps we forgot to hit space and two words ran together
        for suggestion_pair in pmt.twowords(word):
            yield MultiWordSuggestion(suggestion_pair, 'twowords', allow_dash=self.aff.use_dash())

    def ngram_suggestions(self, word: str) -> Iterator[str]:
        def forms_for(word: data.dic.Word, candidate: str):
            # word without prefixes/suffixes is also present...
            # TODO: unless it is forbidden :)
            res = [word.stem]

            suffixes = [
                suffix
                for flag in word.flags
                for suffix in self.aff.SFX.get(flag, [])
                if suffix.cond_regexp.search(word.stem) and candidate.endswith(suffix.add)
            ]
            prefixes = [
                prefix
                for flag in word.flags
                for prefix in self.aff.PFX.get(flag, [])
                if prefix.cond_regexp.search(word.stem) and candidate.startswith(prefix.add)
            ]

            cross = [
                (prefix, suffix)
                for prefix in prefixes
                for suffix in suffixes
                if suffix.crossproduct and prefix.crossproduct
            ]

            for suf in suffixes:
                # FIXME: this things should be more atomic
                root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
                res.append(root + suf.add)

            for pref, suf in cross:
                root = word.stem[len(pref.strip):-len(suf.strip)] if suf.strip else word.stem[len(pref.strip):]
                res.append(pref.add + root + suf.add)

            for pref in prefixes:
                root = word.stem[len(pref.strip):]
                res.append(pref.add + root)

            return res

        # TODO: also NONGRAMSUGGEST and ONLYUPCASE
        # TODO: move to constructor
        bad_flags = {*filter(None, [self.aff.FORBIDDENWORD, self.aff.NOSUGGEST, self.aff.ONLYINCOMPOUND])}

        # FIXME: maybe better to calc it once and for good?..
        roots = (word for word in self.dic.words if not bad_flags.intersection(word.flags))

        yield from ngram_suggest.ngram_suggest(
                    word.lower(),
                    roots=roots,
                    forms_producer=forms_for,
                    maxdiff=self.aff.MAXDIFF,
                    onlymaxdiff=self.aff.ONLYMAXDIFF)

    def phonet_suggestions(self, word: str) -> Iterator[str]:
        if not self.aff.PHONE:
            return

        # TODO: All of it should go to the constructor
        bad_flags = {*filter(None, [self.aff.FORBIDDENWORD, self.aff.NOSUGGEST, self.aff.ONLYINCOMPOUND])}
        roots = (word for word in self.dic.words if not bad_flags.intersection(word.flags))

        yield from phonet.phonet_suggest(word, roots=roots, table=self.aff.PHONE)
