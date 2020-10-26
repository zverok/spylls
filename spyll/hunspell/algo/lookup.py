import re

from enum import Enum
from typing import List, Iterator, Union, Optional

import dataclasses
from dataclasses import dataclass

from spyll.hunspell import data
from spyll.hunspell.data.aff import Flag
from spyll.hunspell.algo.capitalization import Type as CapType
import spyll.hunspell.algo.permutations as pmt

CompoundPos = Enum('CompoundPos', 'BEGIN MIDDLE END')

NUMBER_REGEXP = re.compile(r'^\d+(\.\d+)?$')


# AffixForm is a hypothesis of how some word might be split into stem, suffixes and prefixes.
# It always has full text and stem, and may have up to two suffixes, and up to two prefixes.
# (Affix form without any affix is also valid.)
#
# The following is always true (if we consider absent affixes just empty string):
#
# prefix + prefix2 + stem + suffix2 + suffix = text
#
# prefix2/suffix2 are "secondary", so if the word has only one suffix, it is stored in ``suffix`` and
# ``suffix2`` is ``None``.
#
# If the word form's stem is found is dictionary ``in_dictionary`` attribute is present (though it
# does not implies that dictionary word is compatible with suffixes and prefixes).
#
@dataclass
class AffixForm:
    text: str

    stem: str

    prefix: Optional[data.aff.Prefix] = None
    suffix: Optional[data.aff.Suffix] = None
    prefix2: Optional[data.aff.Prefix] = None
    suffix2: Optional[data.aff.Suffix] = None

    in_dictionary: Optional[data.dic.Word] = None

    def replace(self, **changes):
        return dataclasses.replace(self, **changes)

    def is_base(self):
        return not self.suffix and not self.prefix

    def flags(self):
        flags = self.in_dictionary.flags if self.in_dictionary else set()
        if self.prefix:
            flags = flags.union(self.prefix.flags)
        if self.suffix:
            flags = flags.union(self.suffix.flags)

        return flags

    def all_affixes(self):
        return compact(self.prefix2, self.prefix, self.suffix, self.suffix2)

    def __repr__(self):
        result = f'AffixForm({self.text} = '
        if self.prefix:
            result += f'{self.prefix!r} + '
        if self.prefix2:
            result += f'{self.prefix2!r} + '
        result += self.stem
        if self.suffix2:
            result += f' + {self.suffix2!r}'
        if self.suffix:
            result += f' + {self.suffix!r}'
        result += ')'
        return result


# CompoundForm is a hypothesis of how some word could be split into several AffixForms (word parts
# with their own stems, and possible affixes).
# Typically, only first part of compound is allowed to have prefix, and only last part is allowed
# to have suffix, but there are languages where middle parts can have affixes too, which is
# specified by special flags.
CompoundForm = List[AffixForm]


# Every word form (hypothesis about "this string may correspond to known affixes/dictionary this way")
# is either affix form, or compound one.
WordForm = Union[AffixForm, CompoundForm]


class Lookup:
    def __init__(self, aff: data.aff.Aff, dic: data.dic.Dic):
        self.aff = aff
        self.dic = dic

    # The outermost word correctness check.
    #
    # Basically, prepares word for check (converting/removing chars), and then checks whether
    # the word is properly spelled. If it is not, also tries to break word by break-points (like
    # dashes), and check each part separately.
    #
    # Boolean flags are used when the Lookup is called from Suggest, meaning:
    #
    # * ``capitalization`` -- if ``False``, check ONLY exactly this capitalization
    # * ``allow_nosuggest`` -- if ``False``, don't consider correct words with NOSUGGEST flag
    # * ``allow_break`` -- if ``False``, don't try to break word by dashes and check separately
    #
    def __call__(self, word: str, *,
                 capitalization=True,
                 allow_nosuggest=True,
                 allow_break=True) -> bool:

        # The word is considered correct, if it can be deconstructed into a "good form" (the form
        # that is possible to produce from current dictionary: either it is stem with some affixes,
        # or compound word: list of stem+affixes groups.
        def is_correct(w):
            return any(self.good_forms(w, capitalization=capitalization, allow_nosuggest=allow_nosuggest))

        # If there are entries in the dictionary matching the entire word, and all of those entries
        # are marked with "forbidden" flag, this word can't be considered correct.
        if self.aff.FORBIDDENWORD and self.dic.has_flag(word, self.aff.FORBIDDENWORD, for_all=True):
            return False

        # Convert word before lookup with ICONV table: usually, it is normalization of apostrophes,
        # UTF chars with diacritics (which might have several different forms), and such.
        # See ``aff.ConvTable`` for the full algorithm (it is more complex than just replace one
        # substring with another).
        if self.aff.ICONV:
            word = self.aff.ICONV(word)

        # Remove characters that should be ignored (for example, in Arabic and Hebrew, vowels should
        # be removed before spellchecking)
        if self.aff.IGNORE:
            word = word.translate(self.aff.IGNORE.tr)

        # Numbers are allowed and considered "good word" always
        # TODO: check in hunspell's code, if there are some exceptions?..
        if NUMBER_REGEXP.fullmatch(word):
            return True

        # If the whole word is correct
        if is_correct(word):
            return True

        # ``allow_break=False`` might've been passed from ``Suggest`` and mean we shouldn't try to
        # break word.
        if not allow_break:
            return False

        # ``try_break`` recursively produces all possible lists of word breaking by break patterns
        # (like dashes). For example, if we are checking the word "pre-processed-meat", we'll
        # have ["pre", "processed-meat"], ["pre", "processed", "meat"] and ["pre-processed", "meat"].
        # This is necessary (instead of just breaking the word by all breakpoints, and checking
        # ["pre", "processed", "meat"]), because the dictionary might contain word "pre-processed"
        # as a separate entity, so ["pre-processed", "meat"] would be considered correct, and the
        # other two would not, if there is no separate entry on "pre".
        for parts in self.try_break(word):
            # If all parts in this variant of the breaking is correct, the whole word considered correct.
            if all(is_correct(part) for part in parts if part):
                return True

        return False

    def try_break(self, text, depth=0):
        if depth > 10:
            return

        yield [text]
        for pat in self.aff.BREAK:
            for m in re.finditer(pat.regexp, text):
                start = text[:m.start(1)]
                rest = text[m.end(1):]
                for breaking in self.try_break(rest, depth=depth+1):
                    yield [start, *breaking]

    # The main producer of correct word forms (e.g. ways the proposed string might correspond to our
    # dictionary/affixes). If there is at least one, the word is correctly spelled. There could be
    # many correct forms for one spelling (e.g. word "building" might be a noun "building", or infinitive
    # "build + ing").
    #
    # The method returns generator (forms are produced lazy), so it doesn't have performance
    # overhead when just needs to check "any correct form exists".
    #
    # Might be also used for investigative/debugging purpose this way:
    #
    # dic = Dictionary.from_files('dictionaries/en_US')
    # print(*dic.lookuper.good_forms('spells'))
    # # => AffixForm(spells = spells) -- option 1: "spells" is the whole word, present in dictionary
    # # => AffixForm(spells = spell + Suffix(s: S×, on [[^sxzhy]]$)) -- option 2: word "spell" + suffix "s"
    def good_forms(self, word: str, *,
                   capitalization=True,
                   allow_nosuggest=True) -> Iterator[WordForm]:

        # "capitalization" might be ``False`` if it is passed from ``Suggest``, meaning "check only
        # this exact case"
        if capitalization:
            # Collaction calculates
            # * word's capitalization (none -- all letters are small, init -- first
            # letter is capitalized, all -- all leters are capital, HUH -- some letters are small,
            # some capitalized, first is small; HUHINIT -- same, but the first is capital)
            # * how it might've looked in the dictionary, if we assume the current form is correct
            #
            # For example, if we pass "Cat", the captype would be INIT, and variants ["Cat", "cat"],
            # the latter would be found in dictionary. If we pass "Paris", captype is INIT, variants
            # are ["Paris", "paris"], and the _first_ one is found in the dictionary; that's why
            # we need to check all variants.
            #
            # See ``capitalization.Collation`` for capitalization quirks.
            captype, variants = self.aff.collation.variants(word)
        else:
            captype = self.aff.collation.guess(word)
            variants = [word]

        # Now, for each of capitalization variants possible
        for variant in variants:
            # ...we yield all possible affix forms
            yield from self.affix_forms(variant, captype=captype, allow_nosuggest=allow_nosuggest)
            # ...and then all possible compound forms
            yield from self.compound_forms(variant, captype=captype, allow_nosuggest=allow_nosuggest)

    # Produces correct affix forms of the given words, e.g. all ways in which it can be split into
    # stem+affixes, such that the stem would be present in the dictionary, and stem and all affixes
    # would be compatible with each other.
    #
    # prefix flags, suffix flags, forbidden flags and compoundpos are passed when the method is
    # called from ``compound_xxx`` family of methods.
    def affix_forms(self,
                    word: str,
                    captype: CapType,
                    allow_nosuggest=True,
                    prefix_flags: List[Flag] = [],
                    suffix_flags: List[Flag] = [],
                    forbidden_flags: List[Flag] = [],
                    compoundpos: Optional[CompoundPos] = None,
                    with_forbidden=False) -> Iterator[AffixForm]:

        def is_good_form(form, **kwarg):
            return self.is_good_form(form, compoundpos=compoundpos,
                                     captype=captype,
                                     allow_nosuggest=allow_nosuggest,
                                     **kwarg)

        for form in self.produce_affix_forms(word, compoundpos=compoundpos,
                                             prefix_flags=prefix_flags, suffix_flags=suffix_flags,
                                             forbidden_flags=forbidden_flags):
            found = False
            # Base (no suffixes) homonym is allowed if exists.
            # And if it would not, we would not be here at all.
            if compoundpos or not form.is_base():
                if not with_forbidden and self.dic.has_flag(form.stem, self.aff.FORBIDDENWORD):
                    return

            for homonym in self.dic.homonyms(form.stem):
                candidate = form.replace(in_dictionary=homonym)
                if is_good_form(candidate):
                    found = True
                    yield candidate

            # If it then might be required by compound end to be capitalized, we should find it EVEN
            # if the check is "without checking different capitalizations"
            if self.aff.FORCEUCASE and captype == CapType.INIT and compoundpos == CompoundPos.BEGIN:
                for homonym in self.dic.homonyms(form.stem.lower()):
                    candidate = form.replace(in_dictionary=homonym)
                    if is_good_form(candidate):
                        found = True
                        yield candidate

            if not found and not compoundpos:
                for homonym in self.dic.homonyms(form.stem, ignorecase=True):
                    candidate = form.replace(in_dictionary=homonym)
                    if is_good_form(candidate, check_cap=True):
                        yield candidate

    # Produces all correct compound forms.
    # Delegates all real work to two different compounding algorithms, and then just check if their
    # results pass various correctness checks.
    def compound_forms(self, word: str, captype: CapType, allow_nosuggest=True) -> Iterator[CompoundForm]:
        # The first algorithm is: split the word into several, in all possible ways, and check if
        # some combination of them are dictionary words having flags allowing them to be in compound
        # words. This algorithm should only be used if the relevant flags are present (otherwise,
        # there is nothing to mark words with).
        if self.aff.COMPOUNDBEGIN or self.aff.COMPOUNDFLAG:
            for compound in self.compounds_by_flags(word, captype=captype, allow_nosuggest=allow_nosuggest):
                # When we already produced a compounding hypothesis (meaning every part is present
                # in the dictionary, and allowed to be in this place in a compound), there are still
                # a lot of possible conditions why this form is _incorrect_ all in all, and we need
                # to check them.
                if not self.is_bad_compound(compound, captype):
                    yield compound

        # Another algorithm is: split the word into several, and check if their flag combination is
        # declared as a "compound rule". Obviosly, needs checking only if some compound rules ARE
        # declared.
        if self.aff.COMPOUNDRULE:
            for compound in self.compounds_by_rules(word, allow_nosuggest=allow_nosuggest):
                # Same as above
                if not self.is_bad_compound(compound, captype):
                    yield compound

    # Affixes-related algorithms
    # --------------------------

    def produce_affix_forms(self,
                            word: str,
                            prefix_flags: List[Flag],
                            suffix_flags: List[Flag],
                            forbidden_flags: List[Flag],
                            compoundpos: Optional[CompoundPos] = None) -> Iterator[AffixForm]:

        yield AffixForm(text=word, stem=word)    # "Whole word" is always existing option

        suffix_allowed = compoundpos in [None, CompoundPos.END] or self.aff.COMPOUNDPERMITFLAG
        prefix_allowed = compoundpos in [None, CompoundPos.BEGIN] or self.aff.COMPOUNDPERMITFLAG

        if suffix_allowed:
            yield from self.desuffix(word, required_flags=suffix_flags, forbidden_flags=forbidden_flags)

        if prefix_allowed:
            for form in self.deprefix(word, required_flags=prefix_flags, forbidden_flags=forbidden_flags):
                yield form

                if suffix_allowed and form.prefix and form.prefix.crossproduct:
                    yield from (
                        form2.replace(text=form.text, prefix=form.prefix)
                        for form2 in self.desuffix(form.stem,
                                                   required_flags=suffix_flags,
                                                   forbidden_flags=forbidden_flags,
                                                   crossproduct=True)
                    )

    def desuffix(self, word: str,
                 required_flags: List[Flag],
                 forbidden_flags: List[Flag],
                 nested: bool = False,
                 crossproduct: bool = False) -> Iterator[AffixForm]:

        def good_suffix(suffix):
            return (not crossproduct or suffix.crossproduct) and \
                    all(f in suffix.flags for f in required_flags) and \
                    all(f not in suffix.flags for f in forbidden_flags)

        possible_suffixes = (
            suffix
            for suffix in self.aff.suffixes_index.lookup(word[::-1])
            if good_suffix(suffix) and suffix.lookup_regexp.search(word)
        )

        for suffix in possible_suffixes:
            stem = suffix.replace_regexp.sub(suffix.strip, word)

            yield AffixForm(word, stem, suffix=suffix)

            if not nested:  # only one level depth
                for form2 in self.desuffix(stem,
                                           required_flags=[suffix.flag, *required_flags],
                                           forbidden_flags=forbidden_flags,
                                           nested=True,
                                           crossproduct=crossproduct):
                    yield form2.replace(suffix2=suffix, text=word)

    def deprefix(self, word: str,
                 required_flags: List[Flag],
                 forbidden_flags: List[Flag],
                 nested: bool = False) -> Iterator[AffixForm]:

        def good_prefix(prefix):
            return all(f in prefix.flags for f in required_flags) and \
                   all(f not in prefix.flags for f in forbidden_flags)

        possible_prefixes = (
            prefix
            for prefix in self.aff.prefixes_index.lookup(word)
            if good_prefix(prefix) and prefix.lookup_regexp.search(word)
        )

        for prefix in possible_prefixes:
            stem = prefix.lookup_regexp.sub(prefix.strip, word)

            yield AffixForm(word, stem, prefix=prefix)

            # TODO: Only if compoundprefixes are allowed in *.aff
            if not nested:  # only one level depth
                for form2 in self.deprefix(stem,
                                           required_flags=[prefix.flag, *required_flags],
                                           forbidden_flags=forbidden_flags,
                                           nested=True):
                    yield form2.replace(prefix2=prefix, text=word)

    def is_good_form(self,
                     form: AffixForm,
                     compoundpos: Optional[CompoundPos],
                     captype: CapType,
                     allow_nosuggest=True,
                     check_cap=False) -> bool:

        aff = self.aff

        # Shouldn't happen, just to make mypy happy (to not complain "if root is None, you can't take its flags" below)
        if not form.in_dictionary:
            return False

        root_flags = form.in_dictionary.flags
        all_flags = form.flags()
        # TODO: Should be guessed on dictionary loading
        root_capitalization = aff.collation.guess(form.in_dictionary.stem)

        # investigate = (form.prefix and form.prefix.flag == 'D' and form.suffix and form.suffix.flag == 'A')

        if not allow_nosuggest and aff.NOSUGGEST in root_flags:
            return False

        # Check capitalization
        if captype != root_capitalization:
            if aff.KEEPCASE in root_flags and not aff.CHECKSHARPS:
                return False
            # If the dictionary word is not lowercase, we accept only exactly that
            # case, or ALLCAPS
            if check_cap and captype != CapType.ALL and root_capitalization != CapType.NO:
                return False

        # Check affix flags

        if aff.NEEDAFFIX:
            if aff.NEEDAFFIX in root_flags and form.is_base():
                return False
            if not form.is_base() and all(aff.NEEDAFFIX in a.flags for a in form.all_affixes()):
                return False

        if form.prefix and form.prefix.flag not in all_flags:
            return False
        if form.suffix and form.suffix.flag not in all_flags:
            return False

        if aff.CIRCUMFIX:
            if form.suffix and aff.CIRCUMFIX in form.suffix.flags and \
               not (form.prefix and aff.CIRCUMFIX in form.prefix.flags):
                return False

            if form.prefix and aff.CIRCUMFIX in form.prefix.flags and \
               not (form.suffix and aff.CIRCUMFIX in form.suffix.flags):
                return False

        # Check compound flags

        if not compoundpos:
            return aff.ONLYINCOMPOUND not in all_flags
        if aff.COMPOUNDFLAG in all_flags:
            return True
        if compoundpos == CompoundPos.BEGIN:
            return aff.COMPOUNDBEGIN in all_flags
        if compoundpos == CompoundPos.END:
            return aff.COMPOUNDEND in all_flags
        if compoundpos == CompoundPos.MIDDLE:
            return aff.COMPOUNDMIDDLE in all_flags

        # shoulnd't happen
        return False

    # Compounding details
    # -------------------

    def compounds_by_flags(self,
                           word_rest: str,
                           prev_parts: List[AffixForm] = [],
                           *,
                           captype: CapType,
                           allow_nosuggest=True) -> Iterator[List[AffixForm]]:

        aff = self.aff
        forbidden_flags = compact(aff.COMPOUNDFORBIDFLAG)
        permitflags = compact(aff.COMPOUNDPERMITFLAG)
        prefix_flags = {
            CompoundPos.BEGIN: [],
            CompoundPos.MIDDLE: permitflags,
            CompoundPos.END: permitflags,
        }
        suffix_flags = {
            CompoundPos.BEGIN: [],
            CompoundPos.MIDDLE: permitflags,
            CompoundPos.END: permitflags,
        }

        # If it is middle of compounding process "the rest of the word is the whole last part" is always
        # possible
        if prev_parts:
            for form in self.affix_forms(word_rest,
                                         captype=captype,
                                         compoundpos=CompoundPos.END,
                                         prefix_flags=permitflags,
                                         forbidden_flags=forbidden_flags,
                                         allow_nosuggest=allow_nosuggest):
                yield [form]
        else:
            # if we try to decompound "forbiddenword's", AND "forbiddenword" with suffix "'s" is forbidden,
            # we shouldn't even try.
            if aff.FORBIDDENWORD and any(aff.FORBIDDENWORD in candidate.flags()
                                         for candidate in
                                         self.affix_forms(word_rest, captype=captype, with_forbidden=True)):
                return

        if len(word_rest) < aff.COMPOUNDMIN * 2 or (aff.COMPOUNDWORDMAX and len(prev_parts) >= aff.COMPOUNDWORDMAX):
            return

        compoundpos = CompoundPos.BEGIN if not prev_parts else CompoundPos.MIDDLE

        for pos in range(aff.COMPOUNDMIN, len(word_rest) - aff.COMPOUNDMIN + 1):
            beg = word_rest[0:pos]
            rest = word_rest[pos:]

            for form in self.affix_forms(beg, captype=captype, compoundpos=compoundpos,
                                         prefix_flags=prefix_flags[compoundpos],
                                         suffix_flags=suffix_flags[compoundpos],
                                         forbidden_flags=forbidden_flags,
                                         allow_nosuggest=allow_nosuggest):
                parts = [*prev_parts, form]
                for others in self.compounds_by_flags(rest, parts, captype=captype,
                                                      allow_nosuggest=allow_nosuggest):
                    yield [form, *others]

            if aff.SIMPLIFIEDTRIPLE and beg[-1] == rest[0]:
                # FIXME: for now, we only try duplicating the first word's letter
                for form in self.affix_forms(beg + beg[-1], captype=captype, compoundpos=compoundpos,
                                             prefix_flags=prefix_flags[compoundpos],
                                             suffix_flags=suffix_flags[compoundpos],
                                             forbidden_flags=forbidden_flags,
                                             allow_nosuggest=allow_nosuggest):
                    parts = [*prev_parts, form]
                    for others in self.compounds_by_flags(rest, parts, captype=captype,
                                                          allow_nosuggest=allow_nosuggest):
                        yield [form.replace(text=beg), *others]

    def compounds_by_rules(self,
                           word_rest: str,
                           prev_parts: List[data.dic.Word] = [],
                           rules: Optional[List[data.aff.CompoundRule]] = None,
                           allow_nosuggest=True) -> Iterator[List[AffixForm]]:

        aff = self.aff
        # initial run
        if rules is None:
            rules = self.aff.COMPOUNDRULE

        # FIXME: ignores flags like FORBIDDENWORD and nosuggest

        # If it is middle of compounding process "the rest of the word is the whole last part" is always
        # possible
        if prev_parts:
            for homonym in self.dic.homonyms(word_rest):
                parts = [*prev_parts, homonym]
                flag_sets = [w.flags for w in parts]
                if any(r.fullmatch(flag_sets) for r in rules):
                    yield [AffixForm(word_rest, word_rest)]

        if len(word_rest) < aff.COMPOUNDMIN * 2 or \
                (aff.COMPOUNDWORDMAX and len(prev_parts) >= aff.COMPOUNDWORDMAX):
            return

        for pos in range(aff.COMPOUNDMIN, len(word_rest) - aff.COMPOUNDMIN + 1):
            beg = word_rest[0:pos]
            for homonym in self.dic.homonyms(beg):
                parts = [*prev_parts, homonym]
                flag_sets = [w.flags for w in parts]
                compoundrules = [r for r in rules if r.partial_match(flag_sets)]
                if compoundrules:
                    by_rules = self.compounds_by_rules(word_rest[pos:], rules=compoundrules, prev_parts=parts)
                    for rest in by_rules:
                        yield [AffixForm(beg, beg), *rest]

    def is_bad_compound(self, compound, captype):
        aff = self.aff

        if aff.FORCEUCASE and captype not in [CapType.ALL, CapType.INIT]:
            if self.dic.has_flag(compound[-1].text, aff.FORCEUCASE):
                return True

        for idx, left_paradigm in enumerate(compound[:-1]):
            left = left_paradigm.text
            right_paradigm = compound[idx+1]
            right = right_paradigm.text

            if aff.COMPOUNDFORBIDFLAG:
                # We don't check right: compoundforbid prohibits words at the beginning and middle
                if self.dic.has_flag(left, aff.COMPOUNDFORBIDFLAG):
                    return True

            if any(self.affix_forms(left + ' ' + right, captype=captype)):
                return True

            if aff.CHECKCOMPOUNDREP:
                for candidate in pmt.replchars(left + right, aff.REP):
                    if isinstance(candidate, str) and any(self.affix_forms(candidate, captype=captype)):
                        return True

            if aff.CHECKCOMPOUNDTRIPLE:
                if len(set(left[-2:] + right[:1])) == 1 or len(set(left[-1:] + right[:2])) == 1:
                    return True

            if aff.CHECKCOMPOUNDCASE:
                right_c = right[0]
                left_c = left[-1]
                if (right_c == right_c.upper() or left_c == left_c.upper()) and right_c != '-' and left_c != '-':
                    return True

            if aff.CHECKCOMPOUNDPATTERN:
                if any(pattern.match(left_paradigm, right_paradigm) for pattern in aff.CHECKCOMPOUNDPATTERN):
                    return True

            if aff.CHECKCOMPOUNDDUP:
                # duplication only forbidden at the end (TODO: check, that's what I guess from test)
                if left == right and idx == len(compound) - 2:
                    return True

        return False


def compact(*args):
    return [*filter(None, args)]
