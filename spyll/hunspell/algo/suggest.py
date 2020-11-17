"""
.. autoclass:: Suggest
    :members:

.. autoclass:: Suggestion
    :members:
.. autoclass:: MultiWordSuggestion
    :members:

"""

from typing import Iterator, List, Set, Union

import dataclasses
from dataclasses import dataclass

from spyll.hunspell import data
from spyll.hunspell.algo.capitalization import Type as CapType
from spyll.hunspell.algo import ngram_suggest, phonet_suggest, permutations as pmt

MAXPHONSUGS = 2


@dataclass
class Suggestion:
    """
    Suggestions is what Suggest produces internally to store enough information about some suggestion
    to make sure it is a good one.
    """

    #: Actual suggestion text
    text: str
    #: Code specifying how suggestion was produced, useful for debugging, typically same as the method
    #: of the permutation which led to this suggestion
    source: str

    #: If False, then checking suggestion validity should be without trying to break it on dashes
    #: (or similar chars, depending on the language). This is used, for example, to check "very good"
    #: suggestions: "foobar" (misspeling) => "foo-bar" considered "very good" ONLY if the dictionary
    #: contains "foo-bar" itself, not "foo" and "bar".
    allow_break: bool = True

    def __repr__(self):
        return f"Suggestion[{self.source}]({self.text})"

    def replace(self, **changes):
        return dataclasses.replace(self, **changes)


@dataclass
class MultiWordSuggestion:
    """
    Represents suggestion to split words into several.
    """
    words: List[str]
    source: str

    allow_dash: bool = True

    def stringify(self, separator=' '):
        return Suggestion(separator.join(self.words), self.source)

    def __repr__(self):
        return f"Suggestion[{self.source}]({self.words!r})"


class Suggest:
    """
    TODO
    """
    def __init__(self, aff: data.Aff, dic: data.Dic, lookup):
        self.aff = aff
        self.dic = dic
        self.lookup = lookup

        # Yeah, that's how hunspell defines whether words can be split by dash in this language:
        # either dash is explicitly mentioned in TRY directive, or TRY directive indicates the
        # language uses Latinic script. So dictionaries omiting TRY directive, or for languages with,
        # say, Cyrillic script not including "-" in it, will never suggest "foobar" => "foo-bar",
        # even if it is the perfectly normal way to spell.
        self.use_dash = '-' in self.aff.TRY or 'a' in self.aff.TRY

        # TODO: also NONGRAMSUGGEST and ONLYUPCASE
        bad_flags = {*filter(None, [self.aff.FORBIDDENWORD, self.aff.NOSUGGEST, self.aff.ONLYINCOMPOUND])}

        self.words_for_ngram = [word for word in self.dic.words if not bad_flags.intersection(word.flags)]

    def __call__(self, word: str) -> Iterator[str]:
        """
        Outer "public" interface: just takes all the Suggestion instances and takes text from them.
        """
        yield from (suggestion.text for suggestion in self.suggest_internal(word))

    def suggest_internal(self, word: str) -> Iterator[Suggestion]:
        """
        Main suggestion search loop.
        """

        # Whether some suggestion (permutation of the word) is an existing and allowed word,
        # just delegates to Lookup
        def is_good_suggestion(word, capitalization=False, allow_break=True):
            return self.lookup(word, allow_nosuggest=False, capitalization=capitalization, allow_break=allow_break)

        # For some set of suggestions, produces only good ones:
        def filter_suggestions(suggestions):
            for suggestion in suggestions:
                # For multiword suggestion,
                if isinstance(suggestion, MultiWordSuggestion):
                    # ...if all of the words is correct
                    if all(is_good_suggestion(word, allow_break=False) for word in suggestion.words):
                        # ...we just convert it to plain text suggestion "word1 word2"
                        yield suggestion.stringify()
                        if suggestion.allow_dash:
                            # ...and "word1-word2" if allowed
                            yield suggestion.stringify('-')
                else:
                    # Singleword suggestion is just yielded if it is good
                    if is_good_suggestion(suggestion.text, allow_break=suggestion.allow_break):
                        yield suggestion

        # The suggestion is considered forbidden if there is ANY homonym in dictionary with flag
        # FORBIDDENWORD. Besides marking swearing words, this feature also allows to include in
        # dictionaries known "correctly-looking but actually non-existent" forms, which might important
        # with very flexive languages.
        def is_forbidden(word):
            return self.aff.FORBIDDENWORD and self.dic.has_flag(word, self.aff.FORBIDDENWORD)

        # This set will gather all good suggestions that were already returned (in order, for example,
        # to not return same suggestion twice)
        handled: Set[str] = set()

        # Suggestions that are already considered good are passed through this method, which converts
        # it to proper capitalization form, and then either yields it (if it is not forbidden,
        # hadn't already seen, etc), or just does nothing.
        # Method is quite lengthy, but is nested because updates and reuses ``handled`` local var
        def handle_found(suggestion, *, check_inclusion=False):
            text = suggestion.text
            # If any of the homonyms has KEEPCASE flag, we shouldn't coerce it from the base form.
            # But CHECKSHARPS flag presence changes the meaning of KEEPCASE...
            if (self.aff.KEEPCASE and not self.aff.CHECKSHARPS) and self.dic.has_flag(text, self.aff.KEEPCASE):
                # Don't try to change text's case
                pass
            else:
                # "Coerce" suggested text from the capitalization that it has in the dictionary, to
                # the capitalization of the misspelled word. E.g., if misspelled was "Kiten", suggestion
                # is "kitten" (how it is in the dictionary), and coercion (what we really want
                # to return to user) is "Kitten"
                text = self.aff.collation.coerce(text, captype)
                # ...but if this particular capitalized form is forbidden, return back to original text
                if text != suggestion.text and is_forbidden(text):
                    text = suggestion.text

            # If the word is forbidden, nothing more to do
            if is_forbidden(text):
                return

            # If we already seen this suggestion, nothing to do
            if text in handled:
                return

            # Sometimes we want to skip suggestions even if they are same as PARTS of already
            # seen ones: for examle, ngram-based suggestions might produce very similar forms, like
            # "impermanent" and "permanent" -- both of them are correct, but if the first is
            # closer (by length/content) to misspelling, there is no point in suggesting the second
            if check_inclusion and any(previous.lower() in text.lower() for previous in handled):
                return

            handled.add(text)
            # Finally, OCONV table in .aff-file might specify what chars to replace in suggestions
            # (for example, "'" to proper typographic "’", or common digraphs)
            text = self.aff.OCONV(text) if self.aff.OCONV else text

            # And here we are!
            yield suggestion.replace(text=text)

        # **Start of the main suggest code**

        # First, produce all possible "good capitalizations" from the provided word. For example,
        # if the word is "MsDonalds", good capitalizations (what it might've been in dictionary) are
        # "msdonalds" (full lowercase) "msDonalds" (first letter lowercased), or maybe "Msdonalds"
        # (only first letter capitalized). Note that "MSDONALDS" (it should've been all caps) is not
        # produced as a possible good form, but checked separately in good_permutations
        captype, variants = self.aff.collation.corrections(word)

        good = False
        very_good = False

        # Check a special case: if it is possible that words would be possible to be capitalized
        # on compounding, then we check capitalized form of the word. If it is correct, that's the
        # only suggestion we ever need.
        if self.aff.FORCEUCASE and captype == CapType.NO:
            for capitalized in self.aff.collation.capitalize(word):
                if is_good_suggestion(capitalized):
                    yield from handle_found(Suggestion(capitalized.capitalize(), 'forceucase'))
                    return  # No more need to check anything

        # Now, for all capitalization variant
        for idx, variant in enumerate(variants):
            # If it is different from original capitalization, and is good, we suggest it
            if idx > 0 and is_good_suggestion(variant):
                yield from handle_found(Suggestion(variant, 'case'))

            # Now check if any of the good permutations would be yielded
            for suggestion in filter_suggestions(self.good_permutations(variant)):
                for res in handle_found(suggestion):
                    # ...and if so, return them and set good flag
                    good = True
                    yield res

            # Now check if any of the VERY good permutations would be yielded
            # (yes, the order in hunspell is this: what we are calling here "very good permutations"
            # is tried AFTER just "good" permutations; but they weight more, see below)
            for suggestion in filter_suggestions(self.very_good_permutations(variant)):
                for res in handle_found(suggestion):
                    very_good = True
                    yield res

            # ...if any _very_ good permutation was found, nothing to check anymore
            if very_good:
                return

            # ...but now we'll check "questionable" permutations (which might produce quite unlikely words) --
            # even if "good" permutations were present; but good permutations would be earlier in the list
            for suggestion in filter_suggestions(self.questionable_permutations(variant)):
                yield from handle_found(suggestion)

        if very_good or good:
            return

        # If there was no "good" or "very good" permutations that were valid words, we might try
        # ngram-based suggestion algorithm: it is slower, but able to find severely misspelled words

        ngrams_seen = 0
        for sug in self.ngram_suggestions(word, handled=handled):
            for res in handle_found(Suggestion(sug, 'ngram'), check_inclusion=True):
                ngrams_seen += 1
                yield res
            if ngrams_seen >= self.aff.MAXNGRAMSUGS:
                break

        # Also, if metaphone transformations (phonetic coding of words) were defined in the .aff file,
        # we might try to use them to produce suggestions

        phonet_seen = 0
        for sug in self.phonet_suggestions(word):
            for res in handle_found(Suggestion(sug, 'phonet'), check_inclusion=True):
                phonet_seen += 1
                yield res
            if phonet_seen >= MAXPHONSUGS:
                break

    def very_good_permutations(self, word: str) -> Iterator[Suggestion]:
        """
        "Very good" suggestions: suggest to split word ("alot" => "a lot"), but for now only yield
        them as a _singular_ word suggestion: if the dictionary has _exact_ entry "a lot", it would
        be considered correct.
        """

        for words in pmt.twowords(word):
            yield Suggestion(' '.join(words), 'spaceword')

            if self.use_dash:
                # "alot" => "a-lot", but make sure it would be checked as a whole word (see allow_break
                # usage in Lookup)
                yield Suggestion('-'.join(words), 'spaceword', allow_break=False)

    def good_permutations(self, word: str) -> Iterator[Union[Suggestion, MultiWordSuggestion]]:
        """
        Good permutations (that produces words not very different from the initial one)
        """

        # suggestions for an uppercase word (html -> HTML)
        yield Suggestion(self.aff.collation.upper(word), 'uppercase')

        # REP table in affix file specifies "typical misspellings", and we try to replace them.
        # Note that the content of REP table taken not only from aff file, but also from "ph:" tag
        # in dictionary (lines looking like ``hello ph:helo`` put word "hello" in dictionary, and
        # "helo -> hello" in REP-table), see read_dic.
        #
        # It might return several words if REP table has "REP <something> <some>_<thing>" (_ is code
        # for space).
        #
        # ...in this case we should suggest both "<word1> <word2>" as one dictionary entry, and
        # "<word1>" "<word1>" as a sequence -- but clarifying this sequence might NOT be joined by "-"
        for suggestion in pmt.replchars(word, self.aff.REP):
            if isinstance(suggestion, list):
                yield Suggestion(' '.join(suggestion), 'replchars')
                yield MultiWordSuggestion(suggestion, 'replchars', allow_dash=False)
            else:
                yield Suggestion(suggestion, 'replchars')

    def questionable_permutations(self, word: str) -> Iterator[Union[Suggestion, MultiWordSuggestion]]:
        """
        Permutations that are producing suggestions further from the original word.
        Order is important: As the whole ``Suggest`` produces generator, client code may consume it
        one-by-one, so the first suggested means more likely.
        """

        # MAP in aff file specifies related chars (for example, "ïi"), and mapchars produces all
        # changes of the word with related chars replaced. For example, "naive" produces "naïve".
        for suggestion in pmt.mapchars(word, self.aff.MAP):
            yield Suggestion(suggestion, 'mapchars')

        # Try to swap adjacent characters (ktiten -> kitten), produces all possible forms with ONE
        # swap; but for 4- and 5-letter words tries also two swaps "ahev -> have"
        for suggestion in pmt.swapchar(word):
            yield Suggestion(suggestion, 'swapchar')

        # Try longer swaps (up to 4 chars distance)
        for suggestion in pmt.longswapchar(word):
            yield Suggestion(suggestion, 'longswapchar')

        # Try to replace chars by those close on keyboard ("wueue" -> "queue"), KEY in aff file specifies
        # keyboard layout.
        for suggestion in pmt.badcharkey(word, self.aff.KEY):
            yield Suggestion(suggestion, 'badcharkey')

        # Try remove character (produces all forms with one char removed: "clat" => "lat", "cat", "clt", "cla")
        for suggestion in pmt.extrachar(word):
            yield Suggestion(suggestion, 'extrachar')

        # Try insert character (from set of all possible language chars specified in aff), produces
        # all forms with any of the TRY chars inserted in all possible positions
        for suggestion in pmt.forgotchar(word, self.aff.TRY):
            yield Suggestion(suggestion, 'forgotchar')

        # Try to move a character forward and backwars:
        #  "rnai" => "nari", "nair", "rain" (forward: r moved 2 and 3 chars, n moved 2 chars)
        #         => "rina", "irna", "arni" (backward: i moved 2 and 3 chars, a moved 2 chars)
        # (no 1-char movements necessary, they are covered by swapchar above)
        for suggestion in pmt.movechar(word):
            yield Suggestion(suggestion, 'movechar')

        # Try replace each character with any of other language characters
        for suggestion in pmt.badchar(word, self.aff.TRY):
            yield Suggestion(suggestion, 'badchar')

        # Try fix two-character doubling: "chickcken" -> "chicken" (one-character doubling is
        # already covered by extrachar)
        for suggestion in pmt.doubletwochars(word):
            yield Suggestion(suggestion, 'doubletwochars')

        if not self.aff.NOSPLITSUGS:
            # Try split word by space in all possible positions
            # NOSPLITSUGS option in aff prohibits it, it is important, say, for Scandinavian languages
            for suggestion_pair in pmt.twowords(word):
                yield MultiWordSuggestion(suggestion_pair, 'twowords', allow_dash=self.use_dash)

    def ngram_suggestions(self, word: str, handled: Set[str]) -> Iterator[str]:
        """
        See :mod:`ngram_suggest`
        """
        if self.aff.MAXNGRAMSUGS == 0:
            return

        yield from ngram_suggest.ngram_suggest(
                    word.lower(),
                    dictionary_words=self.words_for_ngram,
                    prefixes=self.aff.PFX, suffixes=self.aff.SFX,
                    known={*(word.lower() for word in handled)},
                    maxdiff=self.aff.MAXDIFF,
                    onlymaxdiff=self.aff.ONLYMAXDIFF)

    def phonet_suggestions(self, word: str) -> Iterator[str]:
        """
        See :mod:`phonet_suggest`
        """
        if not self.aff.PHONE:
            return

        yield from phonet_suggest.phonet_suggest(word, dictionary_words=self.words_for_ngram, table=self.aff.PHONE)
