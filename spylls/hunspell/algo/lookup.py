"""
The main "is this word correct?" algorithm implementation.

On a bird-eye view level:

* word correctness check is implemented as an attempt to analyze word form
  (maybe it has this suffix? maybe it has this prefix? maybe it consists of several words? maybe they
  have suffixes and prefixes?)
* the word considered correct if at least one such form found, that
  it has valid suffixes/prefixes from .aff file and valid stem from .dic file, and they all compatible
  with each other.

To follow algorithm details, start reading from :meth:`Lookup.__call__`

.. autoclass:: Lookup

.. autoclass:: AffixForm
    :members:

.. autoclass:: CompoundForm

.. autodata:: WordForm
.. autodata:: CompoundPos
    :annotation:
"""

import re

from enum import Enum
from typing import List, Iterator, Union, Optional

import dataclasses
from dataclasses import dataclass

from spylls.hunspell import data
from spylls.hunspell.algo.capitalization import Type as CapType
import spylls.hunspell.algo.permutations as pmt

NUMBER_REGEXP = re.compile(r'^\d+(\.\d+)?$')


@dataclass
class AffixForm:
    """
    AffixForm is a hypothesis of how some word might be split into stem, suffixes and prefixes.
    It always has full text and stem, and may have up to two suffixes, and up to two prefixes.
    (Affix form without any affix is also valid.)

    The following is always true (if we consider absent affixes just empty string)::

        prefix + prefix2 + stem + suffix2 + suffix = text

    ``prefix2``/``suffix2`` are "secondary", so if the word has only one suffix, it is stored in
    ``suffix`` and ``suffix2`` is ``None``.

    If the word form's stem is found is dictionary ``in_dictionary`` attribute is present (though it
    does not implies that dictionary word is compatible with suffixes and prefixes).
    """

    text: str

    stem: str

    prefix: Optional[data.aff.Prefix] = None
    suffix: Optional[data.aff.Suffix] = None
    prefix2: Optional[data.aff.Prefix] = None
    suffix2: Optional[data.aff.Suffix] = None

    in_dictionary: Optional[data.dic.Word] = None

    def replace(self, **changes):
        return dataclasses.replace(self, **changes)

    def has_affixes(self):
        return self.suffix or self.prefix

    def is_base(self):
        return not self.has_affixes()

    def flags(self):
        flags = self.in_dictionary.flags if self.in_dictionary else set()
        if self.prefix:
            flags = flags.union(self.prefix.flags)
        if self.suffix:
            flags = flags.union(self.suffix.flags)

        return flags

    def all_affixes(self):
        return [*filter(None, [self.prefix2, self.prefix, self.suffix, self.suffix2])]

    def __repr__(self):
        if self.is_base():
            return f'AffixForm({self.text})'

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


@dataclass
class CompoundForm:
    """
    CompoundForm is a hypothesis of how some word could be split into several AffixForms (word parts
    with their own stems, and possible affixes).
    Typically, only first part of compound is allowed to have prefix, and only last part is allowed
    to have suffix, but there are languages where middle parts can have affixes too, which is
    specified by special flags.
    """
    parts: List[AffixForm]


#: Used when checking "whether this word could be part of the compound... specifically its begin/middl/end"
CompoundPos = Enum('CompoundPos', 'BEGIN MIDDLE END')


#: Every word form (hypothesis about "this string may correspond to known affixes/dictionary this way")
#: is either affix form, or compound one.
WordForm = Union[AffixForm, CompoundForm]


class Lookup:
    """
    ``Lookup`` object is created on :class:`Dictionary <spylls.hunspell.dictionary.Dictionary>` reading. Typically,
    you would not use it directly, but you might want for experiments::

        >>> dictionary = Dictionary.from_files('dictionaries/en_US')
        >>> lookup = dictionary.lookuper

        >>> lookup('spylls')
        False
        >>> lookup('spells')
        True

        >>> for form in lookup.good_forms('spells'):
        ...     print(form)
        AffixForm(spells = spells)
        AffixForm(spells = spell + Suffix(s: S×, on [[^sxzhy]]$))

    See :meth:`__call__` as the main entry point for algorithm explanation.

    **Main methods**

    .. automethod:: __call__
    .. automethod:: good_forms

    **Affixes**

    .. automethod:: affix_forms
    .. automethod:: produce_affix_forms
    .. automethod:: is_good_form
    .. automethod:: desuffix
    .. automethod:: deprefix

    **Compounds**

    .. automethod:: compound_forms
    .. automethod:: compounds_by_flags
    .. automethod:: compounds_by_rules
    .. automethod:: is_bad_compound

    **Utility**

    .. automethod:: break_word
    """

    def __init__(self, aff: data.aff.Aff, dic: data.dic.Dic):
        self.aff = aff
        self.dic = dic

    def __call__(self, word: str, *,
                 capitalization: bool = True,
                 allow_nosuggest: bool = True,
                 allow_break: bool = True) -> bool:
        """
        The outermost word correctness check.

        Basically, prepares word for check (converting/removing chars), and then checks whether
        the any good word form can be produced with :meth:`good_forms`.
        If there is none, also tries to break word by break-points (like dashes) with :meth:`break_word`,
        and check each part separately.

        Boolean flags are used when the Lookup is called from :class:`Suggest <spylls.hunspell.algo.suggest.Suggest>`.

        Args:
            word: Word to check

            capitalization: if ``False``, check ONLY exactly this capitalization
            allow_nosuggest: if ``False``, don't consider correct words with ``NOSUGGEST`` flag
            allow_break: if ``False``, don't try to break word by dashes and check separately
        """

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
        # See data.aff.ConvTable_ for the full algorithm (it is more complex than just replace one
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

        # ``allow_break=False`` might've been passed from Suggest_ and mean we shouldn't try to
        # break word.
        if not allow_break:
            return False

        # ``try_break`` recursively produces all possible lists of word breaking by break patterns
        # (like dashes).
        for parts in self.break_word(word):
            # If all parts in this variant of the breaking is correct, the whole word considered correct.
            if all(is_correct(part) for part in parts if part):
                return True

        return False

    def break_word(self, text, depth=0):
        """
        Recursively produce all possible lists of word breaking by break patterns
        (like dashes). For example, if we are checking the word "pre-processed-meat", we'll
        have ["pre", "processed-meat"], ["pre", "processed", "meat"] and ["pre-processed", "meat"].
        This is necessary (instead of just breaking the word by all breakpoints, and checking
        ["pre", "processed", "meat"]), because the dictionary might contain word "pre-processed"
        as a separate entity, so ["pre-processed", "meat"] would be considered correct, and the
        other two would not, if there is no separate entry on "pre".
        """
        if depth > 10:
            return

        yield [text]
        for pat in self.aff.BREAK:
            for m in pat.regexp.finditer(text):
                start = text[:m.start(1)]
                rest = text[m.end(1):]
                for breaking in self.break_word(rest, depth=depth+1):
                    yield [start, *breaking]

    def good_forms(self, word: str, *,
                   capitalization: bool = True,
                   allow_nosuggest: bool = True) -> Iterator[WordForm]:
        """
        The main producer of correct word forms (e.g. ways the proposed string might correspond to our
        dictionary/affixes). If there is at least one, the word is correctly spelled. There could be
        many correct forms for one spelling:

            >>> lookuper.good_forms('building')
            AffixForm(building = building)                              # noun
            AffixForm(building = build + Suffix(ing: G×, on [[^e]]$))   # verb infinitive

        The method returns generator (forms are produced lazy), so it doesn't have performance
        overhead when just needs to check "any correct form exists".

        Internally:

        * decides all word's possible casings ("KITTEN" -> "kitten", "Kitten", "KITTEN")
        * for each of them, tries to find good affixed forms with :meth:`affix_forms`
        * ...and then good compound forms with :meth:`compound_forms`

        Args:
            word: Word to check

            capitalization: if ``False``, produces forms with ONLY exactly this capitalization
            allow_nosuggest: if ``False``, don't consider correct words with ``NOSUGGEST`` flag
        """

        # "capitalization" might be ``False`` if it is passed from ``Suggest``, meaning "check only
        # this exact case"
        if capitalization:
            # Casing calculates:
            #
            # * word's capitalization (none -- all letters are small, init -- first
            # letter is capitalized, all -- all leters are capital, HUH -- some letters are small,
            # some capitalized, first is small; HUHINIT -- same, but the first is capital)
            # * how it might've looked in the dictionary, if we assume the current form is correct
            #
            # For example, if we pass "Cat", the ``captype`` would be ``INIT``, and variants ``["Cat", "cat"]``,
            # the latter would be found in dictionary. If we pass "Paris", ``captype`` is ``INIT``, variants
            # are ``["Paris", "paris"]``, and the *first* one is found in the dictionary; that's why
            # we need to check all variants.
            #
            # See :class:`Casing <spylls.hunspell.algo.capitalization.Casing>` for capitalization quirks.
            captype, variants = self.aff.casing.variants(word)
        else:
            captype = self.aff.casing.guess(word)
            variants = [word]

        # Now, for each of capitalization variants possible
        for variant in variants:
            # ...we yield all possible affix forms
            for form in self.affix_forms(variant, captype=captype, allow_nosuggest=allow_nosuggest):
                # There is one funny condition in Hunspell for German words:
                # * generally, "ß" is capitalized as "SS"
                # * ...but allowed to be non-capitalized in uppercase words (STRAßE)
                # * ...but there is a special clause for this situation: if the word in dictionary
                #   is marked with "KEEPCASE" flag, the "STRAßE" is NOT allowed, only "STRASSE"
                # ...and we can check it only this late.
                # Fun fact: no known German dictionary uses this trick, actually...
                if (self.aff.CHECKSHARPS and self.aff.KEEPCASE and        # pylint: disable=too-many-boolean-expressions
                        'ß' in form.in_dictionary.stem and self.aff.KEEPCASE in form.flags() and   # type: ignore
                        captype == CapType.ALL and 'ß' in word):
                    continue

                yield form

            # ...and then all possible compound forms
            yield from self.compound_forms(variant, captype=captype, allow_nosuggest=allow_nosuggest)

    def affix_forms(self,
                    word: str,
                    captype: CapType,
                    allow_nosuggest=True,
                    prefix_flags: List[str] = [],
                    suffix_flags: List[str] = [],
                    forbidden_flags: List[str] = [],
                    compoundpos: Optional[CompoundPos] = None,
                    with_forbidden=False) -> Iterator[AffixForm]:
        """
        Produces correct affix forms of the given words, e.g. all ways in which it can be split into
        stem+affixes, such that the stem would be present in the dictionary, and stem and all affixes
        would be compatible with each other.

            >>> [*lookuper.affix_forms('reboots')]
            [AffixForm(reboots = Prefix(re: A×, on ^[.]) + boot + Suffix(s: S×, on [[^sxzhy]]$))]

        Internally, produces all possible (not necessary correct) forms with :meth:`produce_affix_forms`
        and then filters them with :meth:`is_good_form` (this is very simplified explanation, there
        are a lot of edge cases, see code).

        Args:
            word: the word to produce forms for
            allow_nosuggest: ``False`` is passed from Suggest
            prefix_flags: passed when the method is called from ``compound_xxx`` family of methods, to
                          specify flags the prefix (if exists) **should** have
            suffix_flags: passed when the method is called from ``compound_xxx`` family of methods, to
                          specify flags the suffix (if exists) **should** have
            forbiddne_flags: passed when the method is called from ``compound_xxx`` family of methods, to
                             specify flags the prefix and suffix (if exist) **should not** have
            compoundpos: passed when the method is called from ``compound_xxx`` family of methods
                         (and then checked in :meth:`is_good_form` to see if this form can be at specified
                         place in compound word)
            with_forbidden: passed when producing forms *including those specifically marked as forbidden*,
                            to stop compounding immediately if the forbidden one exists.

        """

        # Just a shortcut to call (quite complicated) form validity method with all relevant params.
        def is_good_form(form, **kwarg):
            return self.is_good_form(form, compoundpos=compoundpos,
                                     captype=captype,
                                     allow_nosuggest=allow_nosuggest,
                                     **kwarg)

        # ``produce_affix_forms`` produces ALL possible forms (split of the word into prefixes +
        # stem + suffixes) with the help of known prefixes and affixes. Now we need to choose only
        # correct ones.
        for form in self.produce_affix_forms(word, compoundpos=compoundpos,
                                             prefix_flags=prefix_flags, suffix_flags=suffix_flags,
                                             forbidden_flags=forbidden_flags):
            found = False

            # There might be several entries for the stem in the dictionary, all with different
            # flags (for example, "spell" as a noun, and "spell" as a verb)
            homonyms = self.dic.homonyms(form.stem)

            # If one of the many homonyms has FORBIDDENWORD flag (and others do not),
            # then the word with this stem *can't* be part of the compound word, and can't have
            # affixes, but still is allowed to exist without them.
            if (not with_forbidden and self.aff.FORBIDDENWORD and
                    (compoundpos or form.has_affixes()) and
                    any(self.aff.FORBIDDENWORD in homonym.flags for homonym in homonyms)):
                return

            for homonym in homonyms:
                # Now, for each possible homonym of word's stem, we check it at is a "good form"
                # (basically, stem's flags & suffixes flags allow to be combined to each other, and
                # also allow to be in compound word, if that's the case).
                candidate = form.replace(in_dictionary=homonym)
                if is_good_form(candidate):
                    found = True
                    yield candidate

            # If it then might be required by compound end to be capitalized, we should find it EVEN
            # if the check is "without checking different capitalizations"
            if compoundpos == CompoundPos.BEGIN and self.aff.FORCEUCASE and captype == CapType.INIT:
                for homonym in self.dic.homonyms(form.stem.lower()):
                    candidate = form.replace(in_dictionary=homonym)
                    if is_good_form(candidate):
                        found = True
                        yield candidate

            if found or compoundpos or captype != CapType.ALL:
                continue

            # One final check should be done by scanning through dictionary in case-insensitive manner
            # if the source word was ALL CAPS: In this case, we might miss cases like
            # "OPENOFFICE.ORG" (in dictionary it is OpenOffice.org, so no forms guessed by collation would match it)
            #
            # dic.homonyms(..., ignorecase=True) checks the word against _lowercased_ stems, so we
            # need to check only for it.
            #
            # FIXME: If Casing.variants would return pairs ("word", captype) for all variants,
            # we wouldn't need to re-guess here:
            if self.aff.casing.guess(word) == CapType.NO:
                for homonym in self.dic.homonyms(form.stem, ignorecase=True):
                    candidate = form.replace(in_dictionary=homonym)
                    if is_good_form(candidate):
                        yield candidate

    def compound_forms(self, word: str, captype: CapType, allow_nosuggest: bool = True) -> Iterator[CompoundForm]:
        """
        Produces all correct compound forms.
        Delegates all real work to two different compounding algorithms: :meth:`compounds_by_flags`
        and :meth:`compounds_by_rules`, and then just check if their results pass various correctness
        checks in :meth:`is_bad_compound`.

        Args:
            word: Word to check

            capitalization: if ``False``, produces forms with ONLY exactly this capitalization
            allow_nosuggest: if ``False``, don't consider correct words with ``NOSUGGEST`` flag
        """

        # if we try to decompound "forbiddenword's", AND "forbiddenword" with suffix "'s" is forbidden,
        # we shouldn't even try.
        if self.aff.FORBIDDENWORD and any(self.aff.FORBIDDENWORD in candidate.flags()
                                          for candidate in
                                          self.affix_forms(word, captype=captype, with_forbidden=True)):
            return

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
                            prefix_flags: List[str],
                            suffix_flags: List[str],
                            forbidden_flags: List[str],
                            compoundpos: Optional[CompoundPos] = None) -> Iterator[AffixForm]:
        """
        Produces all possible affix forms: e.g. for all known suffixes & prefixes, if it looks like
        they are in this word, produce forms ``(prefix + stem + suffix)``.

        Internally, calls :meth:`deprefix` and :meth:`desuffix` to chop off suffixes and prefixes.

        Args:
            word: Word to produce forms from
            compoundpos: If the affix form is analysed to be part of compound, specifies where in compound
                         it will be (whether it can have suffixes/prefixes depends on that)
            prefixflags: If the affix form is analysed to be part of compound, AND its position is
                         such that prefixes aren't allowed by default (middle or ending), this list
                         can specify flags of prefixes that ARE allowed
            suffixflags: If the affix form is analysed to be part of compound, AND its position is
                         such that suffixes aren't allowed by default (beginning or middle), this list
                         can specify flags of suffixes that ARE allowed
            forbidden_flags: If the affix form is analysed to be part of compound, specifies set of
                             flags of suffixex/prefixes that are NOT allowed
        """

        # "Whole word" is always existing option. Note that it might later be rejected in is_good_form
        # if this stem has flag NEEDS_AFFIXES.
        yield AffixForm(text=word, stem=word)

        # It makes sense to check the suffixes only if the word is not in compound, or in compoundend,
        # or there are special "flags that might allow suffix"
        suffix_allowed = compoundpos in [None, CompoundPos.END] or suffix_flags
        # ...and same for prefixes
        prefix_allowed = compoundpos in [None, CompoundPos.BEGIN] or prefix_flags

        if suffix_allowed:
            # Now yield all forms with suffix split out...
            yield from self.desuffix(word, required_flags=suffix_flags, forbidden_flags=forbidden_flags)

        if prefix_allowed:
            # ...and all forms with prefix split out...
            for form in self.deprefix(word, required_flags=prefix_flags, forbidden_flags=forbidden_flags):
                yield form

                # ...and, IF this prefix allowed to be combined with suffixes, also with prefix
                # AND suffix split out
                if suffix_allowed and form.prefix and form.prefix.crossproduct:
                    yield from (
                        form2.replace(text=form.text, prefix=form.prefix)
                        for form2 in self.desuffix(form.stem,
                                                   required_flags=suffix_flags,
                                                   forbidden_flags=forbidden_flags,
                                                   crossproduct=True)
                    )

    def desuffix(self, word: str,
                 required_flags: List[str],
                 forbidden_flags: List[str],
                 nested: bool = False,
                 crossproduct: bool = False) -> Iterator[AffixForm]:
        """
        For given word, produces :class:`AffixForm` with suffix(es) split of the stem.

        Args:
            word: word to chop suffixes of
            crossproduct: used when trying to chop the suffix of already deprefixed form, in this
                          case the suffix should have "cross-production allowed" mark.
            nested: used when the function is called recursively: currently, hunspell (and spylls)
                    allow chopping up to two suffixes (in the future it might become an integer ``depth`` parameter
                    for more than two suffixes analysis).
            required_flags: on compounding, flags that suffix **should** have
            forbidden_flags: on compounding, flags that suffix **should not** have
        """

        def good_suffix(suffix):
            return (
                (not crossproduct or suffix.crossproduct) and
                all(f in suffix.flags for f in required_flags) and
                all(f not in suffix.flags for f in forbidden_flags)
            )

        # We are selecting suffixes that have flags and settings, and their regexp pattern match
        # the provided word.
        possible_suffixes = (
            suffix
            for suffix in self.aff.suffixes_index.lookup(word[::-1])
            if good_suffix(suffix) and suffix.lookup_regexp.search(word)
        )

        # With all of those suffixes, we are producing AffixForms of the word passed
        for suffix in possible_suffixes:
            # stem is produced by removing the suffix, and, optionally, adding the part of the
            # stem (named ``strip``). For example, suffix might be declared as ``(strip=y, add=ier)``,
            # then to restore the original stem from word "prettier" we must remove "ier" and add back "y"
            stem = suffix.replace_regexp.sub(suffix.strip, word)

            yield AffixForm(word, stem, suffix=suffix)

            # Try to remove one more suffix, only one level depth
            if not nested:
                for form2 in self.desuffix(stem,
                                           required_flags=[suffix.flag, *required_flags],
                                           forbidden_flags=forbidden_flags,
                                           nested=True,
                                           crossproduct=crossproduct):
                    yield form2.replace(suffix2=suffix, text=word)

    def deprefix(self, word: str,
                 required_flags: List[str],
                 forbidden_flags: List[str],
                 nested: bool = False) -> Iterator[AffixForm]:
        """
        Everything is the same as for :meth:`desuffix`.
        The method doesn't need ``crossproduct: bool`` setting because in :meth:`produce_affix_forms` we first
        analyse prefixes, and then if they allow cross-production, call desuffix with ``crossproduct=True``
        """

        def good_prefix(prefix):
            return all(f in prefix.flags for f in required_flags) and \
                   all(f not in prefix.flags for f in forbidden_flags)

        possible_prefixes = (
            prefix
            for prefix in self.aff.prefixes_index.lookup(word)
            if good_prefix(prefix) and prefix.lookup_regexp.search(word)
        )

        for prefix in possible_prefixes:
            stem = prefix.replace_regexp.sub(prefix.strip, word)

            yield AffixForm(word, stem, prefix=prefix)

            # Second prefix is tried *only* when there is the setting ``COMPLEXPREFIXES`` in
            # aff-file, which is quite rare.
            #
            # Hunspell doesn't have a test for this (and no wrong lookups should be produced by
            # additional attempt to deprefix), but search for second prefix might be a slowdown
            if not nested and self.aff.COMPLEXPREFIXES:
                for form2 in self.deprefix(stem,
                                           required_flags=[prefix.flag, *required_flags],
                                           forbidden_flags=forbidden_flags,
                                           nested=True):
                    yield form2.replace(prefix2=prefix, text=word)

    def is_good_form(self,
                     form: AffixForm,
                     compoundpos: Optional[CompoundPos],
                     captype: CapType,
                     allow_nosuggest: bool = True) -> bool:
        """
        Decides whether the affix form is allowed, by checking compatibility of its components' flags
        (this stem in its flags list, has flags for this suffix and this prefix) and various other
        conditions. It's complicated! Read the code.

        Args:
            form: Form to filter
            compoundpos: If called from ``compound_xx`` family of methods, position in compound word
            captype: original capitalization type of the checked word
            allow_nosuggest: when called from suggest, is set to ``False``
        """

        # Just to make the code a bit simpler, it asks aff. for tons of different stuff
        aff = self.aff

        # Shouldn't happen, just to make mypy happy (to not complain "if root is None, you can't take its flags" below)
        if not form.in_dictionary:
            return False

        root_flags = form.in_dictionary.flags
        all_flags = form.flags()
        # # TODO: Should be guessed on dictionary loading
        # root_capitalization = aff.casing.guess(form.in_dictionary.stem)

        # If the stem has NOSUGGEST flag, it shouldn't be considered an existing word when called
        # from ``Suggest`` (in other cases allow_nosuggest is True). This allows, for example, to
        # consider swearing words "correct" on spellchecking, but avoid suddenly suggesting them
        # for other misspelled word.
        if not allow_nosuggest and aff.NOSUGGEST in root_flags:
            return False

        # If word is marked with KEEPCASE, it is considered correct ONLY when spelled exactly that
        # way.
        if captype != form.in_dictionary.captype and aff.KEEPCASE in root_flags:
            # but if this is German (with CHECKSHARPS flag), and word has "sharp s", the meaning
            # of KEEPCASE flag is different: "disallow leaving ß in uppercased word, always require
            # SS, but all casing forms are possible"
            if not (aff.CHECKSHARPS and 'ß' in form.in_dictionary.stem):
                return False

        # **Check affix flags**

        # The NEEDAFFIX flag must mark two cases:
        if aff.NEEDAFFIX:
            # "This stem is incorrect without affixes" (and no affixes provided)
            if aff.NEEDAFFIX in root_flags and not form.has_affixes():
                return False
            # "All affixes require additional affixes" (usually, it is one suffix, which is "infix" --
            # should have another suffix after it).
            if form.has_affixes() and all(aff.NEEDAFFIX in a.flags for a in form.all_affixes()):
                return False

        # Prefix might be allowed by: a) stem having this flag or b) suffix having this flag
        # (all flags are made from suffix+prefix+stem flags)
        if form.prefix and form.prefix.flag not in all_flags:
            return False
        # Suffix might be allowed by: a) stem having this flag or b) prefix having this flag
        # (all flags are made from suffix+prefix+stem flags)
        if form.suffix and form.suffix.flag not in all_flags:
            return False

        # CIRCUMFIX flag, if present, used to mark suffix and prefix that should go together: if
        # one of them present and has it, another one should too.
        if aff.CIRCUMFIX:
            suffix_has = form.suffix and aff.CIRCUMFIX in form.suffix.flags
            prefix_has = form.prefix and aff.CIRCUMFIX in form.prefix.flags
            if bool(prefix_has) != bool(suffix_has):
                return False

        # **Check compound flags**

        # If it is not a part of the compound word...
        if not compoundpos:
            # ...it shouldn't have the flag "only allowed inside compounds"
            return aff.ONLYINCOMPOUND not in all_flags

        # But if it is a part of the compound word
        # it should either has a flag allowing it to be in compound on ANY positioin
        if aff.COMPOUNDFLAG in all_flags:
            return True
        # ..or the flag allowing it to be at that precise position.
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
                           *,
                           captype: CapType,
                           depth: int = 0,
                           allow_nosuggest: bool = True) -> Iterator[CompoundForm]:
        """
        Produces all possible compound forms such that every part is a valid affixed form, and all of
        those parts are allowed to be together by flags (e.g. first part either has generic flag
        "allowed in compound", or flag "allowed as a compound beginning", middle part has flag "allowed
        in compound", or "allowed as compound middle" and so on).

        Works recursively by first trying to find the allowed beginning of compound (producing it
        by :meth:`affix_forms`), and if it is found, calling itself with the rest of the word, and so on.

        Args:
            word_rest: the part of the word to split into compounds (entire word initially)
            captype: word's capitalization type
            depth: current recursion depth (0 initially)
            allow_nosuggest: see :meth:`good_forms`
        """

        aff = self.aff

        # Flags that are forbidden for affixes (will be passed to affix_forms)
        forbidden_flags = [aff.COMPOUNDFORBIDFLAG] if aff.COMPOUNDFORBIDFLAG else []
        # Flags that are required for affixes. Are passed to affix_forms, expept for:
        #
        # * for the last form suffix_flags not passed (any suffix will do)
        # * for the first form, prefix_flags not passed (any prefix will do)
        permitflags = [aff.COMPOUNDPERMITFLAG] if aff.COMPOUNDPERMITFLAG else []

        # If it is middle of compounding process "the rest of the word is the whole last part" is always
        # possible, so we should check it as a compound end
        if depth:
            # For all valid ways that the rest of the word might be from dictionary (stem+affixes)...
            for form in self.affix_forms(word_rest,
                                         captype=captype,
                                         compoundpos=CompoundPos.END,
                                         prefix_flags=permitflags,
                                         forbidden_flags=forbidden_flags,
                                         allow_nosuggest=allow_nosuggest):
                # return it to the recursively calling method
                yield CompoundForm([form])

        # Check compounding limitation (if the rest of the word is less than 2 allowed parts, or if
        # the further compounding would produce more parts than allowed)
        if len(word_rest) < aff.COMPOUNDMIN * 2 or (aff.COMPOUNDWORDMAX and depth >= aff.COMPOUNDWORDMAX):
            return

        compoundpos = CompoundPos.MIDDLE if depth else CompoundPos.BEGIN
        prefix_flags = [] if compoundpos == CompoundPos.BEGIN else permitflags

        # Now, check all possible split positions, considering allowed size of compound part.
        # E.g. for COMPOUNDMIN=3, and word is "foobarbaz", the checked possible start of the current
        # chunk are [foo, foob, fooba, foobar]
        for pos in range(aff.COMPOUNDMIN, len(word_rest) - aff.COMPOUNDMIN + 1):
            # Split the word by this position
            beg = word_rest[0:pos]
            rest = word_rest[pos:]

            # And for all possible ways it migh be a valid word...
            for form in self.affix_forms(beg, captype=captype, compoundpos=compoundpos,
                                         prefix_flags=prefix_flags,
                                         suffix_flags=permitflags,
                                         forbidden_flags=forbidden_flags,
                                         allow_nosuggest=allow_nosuggest):
                # Recursively try to split the rest of the word ("the whole rest is compound end" also
                # might be the result)
                for partial in self.compounds_by_flags(rest, captype=captype, depth=depth+1,
                                                       allow_nosuggest=allow_nosuggest):
                    yield CompoundForm([form, *partial.parts])

            # Complication! If the affix has SIMPLIFIEDTRIPLE boolean setting, we must check the
            # possibility that "foobbar" is actually consisting of "foobb" and "bar" (some language
            # rules in this case require the third repeating letter to be dropped).
            if aff.SIMPLIFIEDTRIPLE and beg[-1] == rest[0]:
                # FIXME: for now, we only try duplicating the first word's letter
                for form in self.affix_forms(beg + beg[-1], captype=captype, compoundpos=compoundpos,
                                             prefix_flags=prefix_flags,
                                             suffix_flags=permitflags,
                                             forbidden_flags=forbidden_flags,
                                             allow_nosuggest=allow_nosuggest):
                    for partial in self.compounds_by_flags(rest, captype=captype, depth=depth+1,
                                                           allow_nosuggest=allow_nosuggest):
                        yield CompoundForm([form.replace(text=beg), *partial.parts])

    def compounds_by_rules(self,
                           word_rest: str,
                           prev_parts: List[data.dic.Word] = [],
                           rules: Optional[List[data.aff.CompoundRule]] = None,
                           allow_nosuggest: bool = True) -> Iterator[CompoundForm]:  # pylint: disable=unused-argument
        """
        Different way of producing compound words: by rules, looking like ``A*BC?CD``, where A, B, C, D
        are flags the word might have, and ``*?`` have the same meaning as in regular expressions.

        In this way, we start by finding rules that partially match the word parts at the beginning,
        and then recursively split the rest of the word, limiting rules to those still partially matching
        current set of words.

        Most of the magic happens in :class:`CompoundRule <spylls.hunspell.data.aff.CompoundRule>`

        Args:
            word_rest: the part of the word to split into compounds (entire word initially)
            prev_parts: already produced word parts
            rules: list of rules that are still valid on current stage of recursion (all rules from
                   .aff file initially)
            allow_nosuggest: see :meth:`good_forms`
        """

        aff = self.aff

        # initial run
        if rules is None:
            # We start with all known rules
            rules = self.aff.COMPOUNDRULE

        # FIXME: ignores flags like FORBIDDENWORD and nosuggest

        # If it is middle of compounding process "the rest of the word is the whole last part" is always
        # possible
        if prev_parts:
            for homonym in self.dic.homonyms(word_rest):
                parts = [*prev_parts, homonym]
                flag_sets = [w.flags for w in parts]
                if any(r.fullmatch(flag_sets) for r in rules):
                    yield CompoundForm([AffixForm(word_rest, word_rest)])

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
                    for rest in self.compounds_by_rules(word_rest[pos:], rules=compoundrules, prev_parts=parts):
                        yield CompoundForm([AffixForm(beg, beg), *rest.parts])

    def is_bad_compound(self, compound: CompoundForm, captype: CapType) -> bool:
        """
        After the hypothesis "this word is compound word, consisting of those parts" is produced, even
        if all the parts have appropriate flags (e.g. allowed to be in compound), there still could
        be some settings that make compound "bad" (like, some letter is tripled on the border of words,
        or there exists special COMPOUNDPATTERN prohibiting exactly this).

        Args:
            compound: Form to check currectness of
            captype: Checked word capitalization type
        """

        aff = self.aff

        if aff.FORCEUCASE and captype not in [CapType.ALL, CapType.INIT]:
            if self.dic.has_flag(compound.parts[-1].text, aff.FORCEUCASE):
                return True

        # Now we check all adjacent pairs in the compound parts
        for idx, left_paradigm in enumerate(compound.parts[:-1]):
            left = left_paradigm.text
            right_paradigm = compound.parts[idx+1]
            right = right_paradigm.text

            if aff.COMPOUNDFORBIDFLAG:
                # We don't check right: compoundforbid prohibits words at the beginning and middle
                # TODO: Check?
                if self.dic.has_flag(left, aff.COMPOUNDFORBIDFLAG):
                    return True

            # If "foo bar" is present as a _singular_ dictionary entry, compound word containing
            # "(foo)(bar)" parts is not correct.
            if any(self.affix_forms(left + ' ' + right, captype=captype)):
                return True

            if aff.CHECKCOMPOUNDREP:
                # CHECKCOMPOUNDREP setting tells:
                # If REP-table (suggesting frequent misspelling replacements) is present, and any of the
                # replacements produces valid affix form, the compound can't contain that.
                #
                # FIXME: Or is it valid only for the whole "foobar" compound?..
                for candidate in pmt.replchars(left + right, aff.REP):
                    if isinstance(candidate, str) and any(self.affix_forms(candidate, captype=captype)):
                        return True

            if aff.CHECKCOMPOUNDTRIPLE:
                # CHECKCOMPOUNDTRIPLE setting tells, that if there is triplificatioin of some letter
                # on the bound of two parts (like "foobb" + "bar"), it is not correct compound word
                if len(set(left[-2:] + right[:1])) == 1 or len(set(left[-1:] + right[:2])) == 1:
                    return True

            if aff.CHECKCOMPOUNDCASE:
                # CHECKCOMPOUNDCASE prohibits capitalized letters on the bound of compound parts
                right_c = right[0]
                left_c = left[-1]
                if (right_c == right_c.upper() or left_c == left_c.upper()) and right_c != '-' and left_c != '-':
                    return True

            if aff.CHECKCOMPOUNDPATTERN:
                # compound patterns is special micro-language to mark pairs of words that can't be
                # adjacent parts of compound (by their content or flags)
                if any(pattern.match(left_paradigm, right_paradigm) for pattern in aff.CHECKCOMPOUNDPATTERN):
                    return True

            if aff.CHECKCOMPOUNDDUP:
                # duplication only forbidden at the end (TODO: check, that's what I guess from test)
                if left == right and idx == len(compound.parts) - 2:
                    return True

        return False
