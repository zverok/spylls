import re
import itertools
import functools

from collections import defaultdict
from enum import Enum
from typing import List, Iterator, Union, Optional

import dataclasses
from dataclasses import dataclass

from pygtrie import CharTrie

from spyll.hunspell import data
import spyll.hunspell.algo.capitalization as cap
import spyll.hunspell.algo.permutations as pmt

CompoundPos = Enum('CompoundPos', 'BEGIN MIDDLE END')


class Affixes(CharTrie):
    def lookup(self, prefix):
        return [val for _, vals in self.prefixes(prefix) for val in vals]


@dataclass
class CompoundRule:
    text: str

    def __post_init__(self):
        # TODO: proper flag parsing! Long is (aa)(bb)*(cc), numeric is (1001)(1002)*(1003)
        self.flags = set(re.sub(r'[\*\?]', '', self.text))
        parts = re.findall(r'[^*?][*?]?', self.text)
        self.re = re.compile(self.text)
        self.partial_re = re.compile(
            functools.reduce(lambda res, part: f"{part}({res})?", parts[::-1])
        )

    def fullmatch(self, flag_sets):
        relevant_flags = [self.flags.intersection(f) for f in flag_sets]
        return any(
            self.re.fullmatch(''.join(fc))
            for fc in itertools.product(*relevant_flags)
        )

    def partial_match(self, flag_sets):
        relevant_flags = [self.flags.intersection(f) for f in flag_sets]
        return any(
            self.partial_re.fullmatch(''.join(fc))
            for fc in itertools.product(*relevant_flags)
        )


@dataclass
class CompoundPattern:
    left: str
    right: str
    replacement: Optional[str] = None

    def __post_init__(self):
        self.left_stem, _, self.left_flag = self.left.partition('/')
        self.right_stem, _, self.right_flag = self.right.partition('/')
        if self.left_stem == '0':
            self.left_stem = ''
            self.left_no_affix = True
        else:
            self.left_no_affix = False

        if self.right_stem == '0':
            self.right_stem = ''
            self.right_no_affix = True
        else:
            self.right_no_affix = False

    def match(self, left, right):
        return (left.stem.endswith(self.left_stem)) and (right.stem.startswith(self.right_stem)) and \
               (not self.left_no_affix or not left.is_base()) and \
               (not self.right_no_affix or not right.is_base()) and \
               (not self.left_flag or self.left_flag in left.flags()) and \
               (not self.right_flag or self.right_flag in right.flags())


@dataclass
class WordForm:
    text: str
    stem: str
    prefix: Optional[data.aff.Prefix] = None
    suffix: Optional[data.aff.Suffix] = None
    prefix2: Optional[data.aff.Prefix] = None
    suffix2: Optional[data.aff.Suffix] = None
    root: Optional[data.dic.Word] = None

    def replace(self, **changes):
        return dataclasses.replace(self, **changes)

    def is_base(self):
        return not self.suffix and not self.prefix

    def flags(self):
        flags = self.root.flags if self.root else set()
        if self.prefix:
            flags = flags.union(self.prefix.flags)
        if self.suffix:
            flags = flags.union(self.suffix.flags)

        return flags

    def all_affixes(self):
        return list(filter(None, [self.prefix2, self.prefix, self.suffix, self.suffix2]))


Compound = List[WordForm]


class Counted:
    def __init__(self):
        self.counter = 0

    def count(self, generator):
        for item in generator:
            self.counter += 1
            yield item


class Analyzer:
    def __init__(self, aff: data.aff, dic: data.dic):
        self.aff = aff
        self.dic = dic
        self.compile()

    def compile(self):
        def suffix_regexp(suffix):
            cond_parts = re.findall(r'(\[.+\]|[^\[])', suffix.condition)
            if suffix.strip:
                cond_parts = cond_parts[:-len(suffix.strip)]

            if cond_parts and cond_parts != ['.']:
                cond = '(?<=' + ''.join(cond_parts) + ')'
            else:
                cond = ''
            return re.compile(cond + suffix.add + '$')

        def prefix_regexp(prefix):
            cond_parts = re.findall(r'(\[.+\]|[^\[])', prefix.condition)
            cond_parts = cond_parts[len(prefix.strip):]

            if cond_parts and cond_parts != ['.']:
                cond = '(?=' + ''.join(cond_parts) + ')'
            else:
                cond = ''
            return re.compile('^' + prefix.add + cond)

        suffixes = defaultdict(list)
        for suf in itertools.chain.from_iterable(self.aff.SFX.values()):
            suffixes[suf.add[::-1]].append((suf, suffix_regexp(suf)))

        self.suffixes = Affixes(suffixes)

        prefixes = defaultdict(list)
        for pref in itertools.chain.from_iterable(self.aff.PFX.values()):
            prefixes[pref.add].append((pref, prefix_regexp(pref)))

        self.prefixes = Affixes(prefixes)

        self.compoundrules = [CompoundRule(r) for r in self.aff.COMPOUNDRULE]
        self.compoundpatterns = [CompoundPattern(*row) for row in self.aff.CHECKCOMPOUNDPATTERN]

        self.breakpatterns = [
            re.compile(f"({pat})") if pat.startswith('^') or pat.endswith('$') else re.compile(f".({pat}).")
            for pat in self.aff.BREAK
        ]

        self.collation = cap.Collation(sharp_s=self.aff.CHECKSHARPS, dotless_i=self.aff.LANG in ['tr', 'az', 'crh'])

    def lookup(self, word: str, *,
               capitalization=True,
               with_compounds=None,
               allow_nosuggest=True,
               allow_break=True) -> bool:
        if self.aff.FORBIDDENWORD and self.dic.has_flag(word, self.aff.FORBIDDENWORD, for_all=True):
            return False

        if self.aff.ICONV:
            for (i, o) in sorted(self.aff.ICONV, key=lambda io: len(io[1]), reverse=True):
                word = word.replace(i, o)

        if self.aff.IGNORE:
            word = word.translate(str.maketrans('', '', self.aff.IGNORE))

        def is_found(variant):
            return any(
                self.analyze(variant,
                             with_compounds=with_compounds,
                             capitalization=capitalization,
                             allow_nosuggest=allow_nosuggest)
            )

        # Numbers are allowed and considered "good word" always
        # TODO: check in hunspell's code, if there are some exceptions?..
        if re.fullmatch(r'^\d+(\.\d+)?$', word):
            return True

        if is_found(word):
            return True

        if not allow_break:
            return False

        def try_break(text, depth=0):
            if depth > 10:
                return

            yield [text]
            for pat in self.breakpatterns:
                for m in re.finditer(pat, text):
                    start = text[:m.start(1)]
                    rest = text[m.end(1):]
                    for breaking in try_break(rest, depth=depth+1):
                        yield [start, *breaking]

        for parts in try_break(word):
            if all(is_found(part) for part in parts if part):
                return True

        return False

    def analyze(self, word: str, *,
                capitalization=True,
                with_compounds=None,
                allow_nosuggest=True) -> Iterator[Union[WordForm, Compound]]:

        def analyze_internal(variant, captype):
            if with_compounds is not True:
                yield from self.word_forms(variant, captype=captype, allow_nosuggest=allow_nosuggest)
            if with_compounds is not False:
                yield from self.compound_parts(variant, captype=captype, allow_nosuggest=allow_nosuggest)

        if capitalization:
            captype, variants = self.collation.variants(word)

            for v in variants:
                yield from analyze_internal(v, captype=captype)
        else:
            yield from analyze_internal(word, captype=cap.guess(word))

    def word_forms(
            self,
            word: str,
            captype: cap.Cap,
            compoundpos: Optional[CompoundPos] = None,
            allow_nosuggest=True,
            with_forbidden=False) -> Iterator[WordForm]:

        def good_form(form, **kwarg):
            return self.good_form(form, compoundpos=compoundpos,
                                  captype=captype,
                                  allow_nosuggest=allow_nosuggest,
                                  **kwarg)

        for form in self.try_affix_forms(word, compoundpos=compoundpos):
            found = False
            # Base (no suffixes) homonym is allowed if exists.
            # And if it would not, we would not be here at all.
            if compoundpos or not form.is_base():
                if not with_forbidden and self.dic.has_flag(form.stem, self.aff.FORBIDDENWORD):
                    return

            for homonym in self.dic.homonyms(form.stem):
                candidate = form.replace(root=homonym)
                if good_form(candidate):
                    found = True
                    yield candidate

            # If it then might be required by compound end to be capitalized, we should find it EVEN
            # if the check is "without checking different capitalizations"
            if self.aff.FORCEUCASE and captype == cap.Cap.INIT and compoundpos == CompoundPos.BEGIN:
                for homonym in self.dic.homonyms(form.stem.lower()):
                    candidate = form.replace(root=homonym)
                    if good_form(candidate):
                        found = True
                        yield candidate

            if not found and not compoundpos:
                for homonym in self.dic.homonyms(form.stem, ignorecase=True):
                    candidate = form.replace(root=homonym)
                    if good_form(candidate, check_cap=True):
                        yield candidate

    def compound_parts(self, word: str, captype: cap.Cap, allow_nosuggest=True) -> Iterator[Compound]:
        if self.aff.COMPOUNDBEGIN or self.aff.COMPOUNDFLAG:
            by_flags = self.compound_parts_by_flags(word, captype=captype, allow_nosuggest=allow_nosuggest)
        else:
            by_flags = iter(())

        if self.compoundrules:
            by_rules = self.compound_parts_by_rules(word, allow_nosuggest=allow_nosuggest)
        else:
            by_rules = iter(())

        def bad_compound(compound):
            return self.bad_compound(compound, captype)

        yield from (compound
                    for compound in itertools.chain(by_flags, by_rules)
                    if not bad_compound(compound))

    def good_form(
            self,
            form: WordForm,
            compoundpos: Optional[CompoundPos],
            captype: cap.Cap,
            allow_nosuggest=True,
            check_cap=False) -> bool:

        aff = self.aff

        root_flags = form.root.flags
        all_flags = form.flags()
        root_capitalization = cap.guess(form.root.stem)

        # investigate = (form.prefix and form.prefix.flag == 'D' and form.suffix and form.suffix.flag == 'A')

        if not allow_nosuggest and aff.NOSUGGEST in root_flags:
            return False

        # Check capitalization
        if captype != root_capitalization:
            if aff.KEEPCASE in root_flags and not aff.CHECKSHARPS:
                return False
            # If the dictionary word is not lowercase, we accept only exactly that
            # case, or ALLCAPS
            if check_cap and captype != cap.Cap.ALL and root_capitalization != cap.Cap.NO:
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
        elif aff.COMPOUNDFLAG in all_flags:
            return True
        elif compoundpos == CompoundPos.BEGIN:
            return aff.COMPOUNDBEGIN in all_flags
        elif compoundpos == CompoundPos.END:
            return aff.COMPOUNDEND in all_flags
        elif compoundpos == CompoundPos.MIDDLE:
            return aff.COMPOUNDMIDDLE in all_flags
        else:
            # shoulnd't happen
            return False

    # Affixes-related algorithms
    # --------------------------

    def try_affix_forms(
            self,
            word: str,
            compoundpos: Optional[CompoundPos] = None) -> Iterator[WordForm]:

        yield WordForm(word, word)    # "Whole word" is always existing option

        aff = self.aff

        if compoundpos:
            suffix_allowed = compoundpos == CompoundPos.END or aff.COMPOUNDPERMITFLAG
            prefix_allowed = compoundpos == CompoundPos.BEGIN or aff.COMPOUNDPERMITFLAG
            prefix_required_flags = [] if compoundpos == CompoundPos.BEGIN else [aff.COMPOUNDPERMITFLAG]
            suffix_required_flags = [] if compoundpos == CompoundPos.END else [aff.COMPOUNDPERMITFLAG]
            forbidden_flags = [aff.COMPOUNDFORBIDFLAG] if aff.COMPOUNDFORBIDFLAG else []
        else:
            suffix_allowed = True
            prefix_allowed = True
            prefix_required_flags = []
            suffix_required_flags = []
            forbidden_flags = []

        if suffix_allowed:
            yield from self.desuffix(word, required_flags=suffix_required_flags, forbidden_flags=forbidden_flags)

        if prefix_allowed:
            for form in self.deprefix(word, required_flags=prefix_required_flags, forbidden_flags=forbidden_flags):
                yield form

                if suffix_allowed and form.prefix.crossproduct:
                    yield from (
                        form2.replace(text=form.text, prefix=form.prefix)
                        for form2 in self.desuffix(form.stem,
                                                   required_flags=suffix_required_flags,
                                                   forbidden_flags=forbidden_flags,
                                                   crossproduct=True)
                    )

    def desuffix(
            self,
            word: str,
            required_flags: List[str] = [],
            forbidden_flags: List[str] = [],
            nested: bool = False,
            crossproduct: bool = False) -> Iterator[WordForm]:

        def good_suffix(suffix):
            return (not crossproduct or suffix.crossproduct) and \
                    all(f in suffix.flags for f in required_flags) and \
                    all(f not in suffix.flags for f in forbidden_flags)

        possible_suffixes = (
            (suffix, regexp)
            for suffix, regexp in self.suffixes.lookup(word[::-1])
            if good_suffix(suffix) and regexp.search(word)
        )

        for suffix, regexp in possible_suffixes:
            stem = regexp.sub(suffix.strip, word)

            yield WordForm(word, stem, suffix=suffix)

            if not nested:  # only one level depth
                for form2 in self.desuffix(stem,
                                           required_flags=[suffix.flag, *required_flags],
                                           forbidden_flags=forbidden_flags,
                                           nested=True,
                                           crossproduct=crossproduct):
                    yield form2.replace(suffix2=suffix, text=word)

    def deprefix(
            self,
            word: str,
            required_flags: List[str] = [],
            forbidden_flags: List[str] = [],
            nested: bool = False) -> Iterator[WordForm]:

        def good_prefix(prefix):
            return all(f in prefix.flags for f in required_flags) and \
                   all(f not in prefix.flags for f in forbidden_flags)

        possible_prefixes = (
            (prefix, regexp)
            for prefix, regexp in self.prefixes.lookup(word)
            if good_prefix(prefix) and regexp.search(word)
        )

        for prefix, regexp in possible_prefixes:
            stem = regexp.sub(prefix.strip, word)

            yield WordForm(word, stem, prefix=prefix)

            # TODO: Only if compoundpreffixes are allowed in *.aff
            if not nested:  # only one level depth
                for form2 in self.deprefix(stem,
                                           required_flags=[prefix.flag, *required_flags],
                                           forbidden_flags=forbidden_flags,
                                           nested=True):
                    yield form2.replace(prefix2=prefix, text=word)

    # Compounding details
    # -------------------

    def compound_parts_by_flags(
            self,
            word_rest: str,
            prev_parts: List[WordForm] = [],
            *,
            captype: cap.Cap,
            allow_nosuggest=True) -> Iterator[List[WordForm]]:

        aff = self.aff

        # If it is middle of compounding process "the rest of the word is the whole last part" is always
        # possible
        if prev_parts:
            for form in self.word_forms(word_rest,
                                        captype=captype,
                                        compoundpos=CompoundPos.END,
                                        allow_nosuggest=allow_nosuggest):
                yield [form]
        else:
            # if we try to decompoun "forbiddenword's", AND "forbiddenword" with suffix "'s" is forbidden,
            # we shouldn't even try.
            if aff.FORBIDDENWORD and any(aff.FORBIDDENWORD in candidate.flags()
                                         for candidate in
                                         self.word_forms(word_rest, captype=captype, with_forbidden=True)):
                return

        if len(word_rest) < aff.COMPOUNDMIN * 2 or \
                (aff.COMPOUNDWORDMAX and len(prev_parts) >= aff.COMPOUNDWORDMAX):
            return

        compoundpos = CompoundPos.BEGIN if not prev_parts else CompoundPos.MIDDLE

        for pos in range(aff.COMPOUNDMIN, len(word_rest) - aff.COMPOUNDMIN + 1):
            beg = word_rest[0:pos]
            rest = word_rest[pos:]

            for form in self.word_forms(beg, captype=captype, compoundpos=compoundpos,
                                        allow_nosuggest=allow_nosuggest):
                parts = [*prev_parts, form]
                for others in self.compound_parts_by_flags(rest, parts, captype=captype,
                                                           allow_nosuggest=allow_nosuggest):
                    yield [form, *others]

            if aff.SIMPLIFIEDTRIPLE and beg[-1] == rest[0]:
                # FIXME: for now, we only try duplicating the first word's letter
                for form in self.word_forms(beg + beg[-1], captype=captype, compoundpos=compoundpos,
                                            allow_nosuggest=allow_nosuggest):
                    parts = [*prev_parts, form]
                    for others in self.compound_parts_by_flags(rest, parts, captype=captype,
                                                               allow_nosuggest=allow_nosuggest):
                        yield [form.replace(text=beg), *others]

    def compound_parts_by_rules(
            self,
            word_rest: str,
            prev_parts: List[data.dic.Word] = [],
            rules: Optional[List[CompoundRule]] = None,
            allow_nosuggest=True) -> Iterator[List[WordForm]]:

        aff = self.aff
        # initial run
        if rules is None:
            rules = self.compoundrules

        # FIXME: ignores flags like FORBIDDENWORD and nosuggest

        # If it is middle of compounding process "the rest of the word is the whole last part" is always
        # possible
        if prev_parts:
            for homonym in self.dic.homonyms(word_rest):
                parts = [*prev_parts, homonym]
                flag_sets = [w.flags for w in parts]
                if any(r.fullmatch(flag_sets) for r in rules):
                    yield [WordForm(word_rest, word_rest)]

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
                    by_rules = self.compound_parts_by_rules(word_rest[pos:], rules=rules, prev_parts=parts)
                    for rest in by_rules:
                        yield [WordForm(beg, beg), *rest]

    def bad_compound(self, compound, captype):
        aff = self.aff

        if aff.FORCEUCASE and captype not in [cap.Cap.ALL, cap.Cap.INIT]:
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

            if any(self.word_forms(left + ' ' + right, captype=captype)):
                return True

            if aff.CHECKCOMPOUNDREP:
                for candidate in pmt.replchars(left + right, aff.REP):
                    if isinstance(candidate, str) and any(self.word_forms(candidate, captype=captype)):
                        return True

            if aff.CHECKCOMPOUNDTRIPLE:
                if len(set(left[-2:] + right[:1])) == 1 or len(set(left[-1:] + right[:2])) == 1:
                    return True

            if aff.CHECKCOMPOUNDCASE:
                r = right[0]
                l = left[-1]
                if (r == r.upper() or l == l.upper()) and r != '-' and l != '-':
                    return True

            if aff.CHECKCOMPOUNDPATTERN:
                if any(pattern.match(left_paradigm, right_paradigm) for pattern in self.compoundpatterns):
                    return True

            if aff.CHECKCOMPOUNDDUP:
                # duplication only forbidden at the end (TODO: check, that's what I guess from test)
                if left == right and idx == len(compound) - 2:
                    return True
        return False
