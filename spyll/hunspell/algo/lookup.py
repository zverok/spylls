import itertools
import collections
from enum import Enum
from typing import List, Iterator, Union, Optional

from spyll.hunspell import data
import spyll.hunspell.algo.capitalization as cap

CompoundPos = Enum('CompoundPos', 'BEGIN MIDDLE END')

Paradigm = collections.namedtuple('Paradigm',
                                  ['stem', 'prefix', 'suffix', 'prefix2', 'suffix2'],
                                  defaults=[None, None, None, None]
                                  )

Compound = List[Paradigm]


def analyze(aff: data.Aff, dic: data.Dic, word: str, *,
            capitalization=True,
            allow_nosuggest=True) -> Iterator[Union[Paradigm, Compound]]:

    def analyze_internal(variant, allcap=False):
        return itertools.chain(
            analyze_affixed(aff, dic, variant, allcap=allcap, allow_nosuggest=allow_nosuggest),
            analyze_compound(aff, dic, variant, allow_nosuggest=allow_nosuggest)
        )

    if capitalization:
        captype, variants = cap.variants(word)

        return itertools.chain.from_iterable(
            analyze_internal(v, allcap=(captype == cap.Cap.ALL))
            for v in variants
        )
    else:
        return analyze_internal(word)


def analyze_affixed(
        aff: data.Aff,
        dic: data.Dic,
        word: str,
        allcap: bool = False,
        compoundpos: Optional[CompoundPos] = None,
        allow_nosuggest=True) -> Iterator[Paradigm]:

    for form in split_affixes(aff, word, compoundpos=compoundpos):
        found = False
        for w in dic.homonyms(form.stem):
            if have_compatible_flags(aff, w, form, compoundpos=compoundpos,
                                     allow_nosuggest=allow_nosuggest):
                found = True
                yield form

        if not found:
            for w in dic.homonyms(form.stem, ignorecase=True):
                # If the dictionary word is not lowercase, we accept only exactly that
                # case (above), or ALLCAPS
                if not allcap and cap.guess(w.stem) != cap.Cap.NO:
                    continue
                if have_compatible_flags(aff, w, form, compoundpos=compoundpos,
                                         allow_nosuggest=allow_nosuggest):
                    yield form


def analyze_compound(aff: data.Aff, dic: data.Dic, word: str,
                     allow_nosuggest=True) -> Iterator[Compound]:
    if aff.compoundbegin or aff.compoundflag:
        by_flags = split_compound_by_flags(aff, dic, word, allow_nosuggest=allow_nosuggest)
    else:
        by_flags = iter(())

    if aff.compoundrules:
        by_rules = split_compound_by_rules(aff, dic, word, compoundrules=aff.compoundrules,
                                           allow_nosuggest=allow_nosuggest)
    else:
        by_rules = iter(())

    def bad_compound(compound):

        for left_paradigm in compound[:-1]:
            for right_paradigm in compound[1:]:
                # FIXME: In fact, full words, not stems!
                left = left_paradigm.stem
                right = right_paradigm.stem
                if aff.checkcompoundcase:
                    r = right[0]
                    l = left[-1]
                    if (r == r.upper() or l == l.upper()) and r != '-' and l != '-':
                        return True
        return False


    yield from (compound
     for compound in itertools.chain(by_flags, by_rules)
     if not bad_compound(compound)
    )


def have_compatible_flags(
        aff: data.Aff,
        dictionary_word: data.dic.Word,
        paradigm: Paradigm,
        compoundpos: Optional[CompoundPos],
        allow_nosuggest=True) -> bool:

    all_flags = dictionary_word.flags
    if paradigm.prefix:
        all_flags = all_flags.union(paradigm.prefix.flags)
    if paradigm.suffix:
        all_flags = all_flags.union(paradigm.suffix.flags)

    if aff.forbiddenword in dictionary_word.flags:
        return False

    if not allow_nosuggest and aff.nosuggest in dictionary_word.flags:
        return False

    # Check affix flags
    if not paradigm.suffix and not paradigm.prefix:
        if aff.needaffix in all_flags or aff.pseudoroot in all_flags:
            return False

    if paradigm.prefix and paradigm.prefix.flag not in all_flags:
        return False
    if paradigm.suffix and paradigm.suffix.flag not in all_flags:
        return False

    # Check compound flags

    if not compoundpos:
        return aff.onlyincompound not in all_flags

    if aff.compoundflag in all_flags:
        return True

    if compoundpos == CompoundPos.BEGIN:
        return aff.compoundbegin in all_flags
    elif compoundpos == CompoundPos.END:
        return aff.compoundlast in all_flags
    elif compoundpos == CompoundPos.MIDDLE:
        return aff.compoundmiddle in all_flags
    else:
        # shoulnd't happen
        return False


# Affixes-related algorithms
# --------------------------


def split_affixes(
        aff: data.Aff,
        word: str,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    result = _split_affixes(aff, word, compoundpos=compoundpos)

    # FIXME: I feel like this methods should be simpler!
    # Or at least better explained
    def only_affix_need_affix(form, flag):
        all_affixes = list(filter(None, [form.prefix, form.prefix2, form.suffix, form.suffix2]))
        if not all_affixes:
            return False
        needaffs = [aff for aff in all_affixes if flag in aff.flags]
        return len(all_affixes) == len(needaffs)

    if aff.needaffix:
        # FIXME: why doesn't just return (...generator...) work?..
        yield from (r for r in result if not only_affix_need_affix(r, aff.needaffix))
    else:
        yield from result


def _split_affixes(
        aff: data.Aff,
        word: str,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    yield Paradigm(word)    # "Whole word" is always existing option

    if compoundpos:
        suffix_allowed = compoundpos == CompoundPos.END or aff.compoundpermitflag
        prefix_allowed = compoundpos == CompoundPos.BEGIN or aff.compoundpermitflag
        prefix_required_flags = [] if compoundpos == CompoundPos.BEGIN else [aff.compoundpermitflag]
        suffix_required_flags = [] if compoundpos == CompoundPos.END else [aff.compoundpermitflag]
        forbidden_flags = [aff.compoundforbidflag] if aff.compoundforbidflag else []
    else:
        suffix_allowed = True
        prefix_allowed = True
        prefix_required_flags = []
        suffix_required_flags = []
        forbidden_flags = []

    if suffix_allowed:
        yield from desuffix(aff, word, required_flags=suffix_required_flags, forbidden_flags=forbidden_flags)

    if prefix_allowed:
        for form in deprefix(aff, word, required_flags=prefix_required_flags, forbidden_flags=forbidden_flags):
            yield form

            if suffix_allowed and form.prefix.crossproduct:
                yield from (
                    form2._replace(prefix=form.prefix)
                    for form2 in desuffix(aff, form.stem, required_flags=suffix_required_flags, forbidden_flags=forbidden_flags, crossproduct=True)
                )


def desuffix(
        aff: data.Aff,
        word: str,
        required_flags: List[str] = [],
        forbidden_flags: List[str] = [],
        nested: bool = False,
        crossproduct: bool = False) -> Iterator[Paradigm]:

    def good_suffix(suffix):
        return crossproduct == suffix.crossproduct and \
                all(f in suffix.flags for f in required_flags) and \
                all(f not in suffix.flags for f in forbidden_flags)

    possible_suffixes = (
        suffix
        for suffix in aff.suffixes.lookup(word[::-1])
        if good_suffix(suffix) and suffix.regexp.search(word)
    )

    for suffix in possible_suffixes:
        stem = suffix.regexp.sub(suffix.strip, word)

        yield Paradigm(stem, suffix=suffix)

        if not nested:  # only one level depth
            for form2 in desuffix(aff, stem,
                                  required_flags=[suffix.flag, *required_flags],
                                  forbidden_flags=forbidden_flags,
                                  nested=True,
                                  crossproduct=crossproduct):
                yield form2._replace(suffix2=suffix)


def deprefix(
        aff: data.Aff,
        word: str,
        required_flags: List[str] = [],
        forbidden_flags: List[str] = [],
        nested: bool = False) -> Iterator[Paradigm]:

    def good_prefix(prefix):
        return all(f in prefix.flags for f in required_flags) and \
               all(f not in prefix.flags for f in forbidden_flags)

    possible_prefixes = (
        prefix
        for prefix in aff.prefixes.lookup(word)
        if good_prefix(prefix) and prefix.regexp.search(word)
    )

    for prefix in possible_prefixes:
        stem = prefix.regexp.sub(prefix.strip, word)

        yield Paradigm(stem, prefix=prefix)

        # TODO: Only if compoundpreffixes are allowed in *.aff
        if not nested:  # only one level depth
            for form2 in deprefix(aff, stem,
                                  required_flags=[prefix.flag, *required_flags],
                                  forbidden_flags=forbidden_flags,
                                  nested=True):
                yield form2._replace(prefix2=prefix)


# Compounding details
# -------------------


def split_compound_by_flags(
        aff: data.Aff,
        dic: data.Dic,
        word_rest: str,
        prev_parts: List[Paradigm] = [],
        allow_nosuggest=True) -> Iterator[List[Paradigm]]:

    # If it is middle of compounding process "the rest of the word is the whole last part" is always
    # possible
    if prev_parts:
        for paradigm in analyze_affixed(aff, dic, word_rest,
                                        compoundpos=CompoundPos.END,
                                        allow_nosuggest=allow_nosuggest):
            yield [paradigm]

    if len(word_rest) < aff.compoundmin * 2 or \
            (aff.compoundwordsmax and len(prev_parts) >= aff.compoundwordsmax):
        return

    compoundpos = CompoundPos.BEGIN if not prev_parts else CompoundPos.MIDDLE

    for pos in range(aff.compoundmin, len(word_rest) - aff.compoundmin + 1):
        beg = word_rest[0:pos]

        for paradigm in analyze_affixed(aff, dic, beg, compoundpos=compoundpos,
                                        allow_nosuggest=allow_nosuggest):
            parts = [*prev_parts, paradigm]
            for rest in split_compound_by_flags(aff, dic, word_rest[pos:], parts,
                                                allow_nosuggest=allow_nosuggest):
                yield [paradigm, *rest]


def split_compound_by_rules(
        aff: data.Aff,
        dic: data.Dic,
        word_rest: str,
        compoundrules: List[data.aff.CompoundRule],
        prev_parts: List[data.dic.Word] = [],
        allow_nosuggest=True) -> Iterator[List[Paradigm]]:

    # FIXME: ignores flags like forbiddenword and nosuggest

    # If it is middle of compounding process "the rest of the word is the whole last part" is always
    # possible
    if prev_parts:
        for homonym in dic.homonyms(word_rest):
            parts = [*prev_parts, homonym]
            flag_sets = [w.flags for w in parts]
            if any(r.fullmatch(flag_sets) for r in compoundrules):
                yield [Paradigm(homonym)]

    if len(word_rest) < aff.compoundmin * 2 or \
            (aff.compoundwordsmax and len(prev_parts) >= aff.compoundwordsmax):
        return

    for pos in range(aff.compoundmin, len(word_rest) - aff.compoundmin + 1):
        beg = word_rest[0:pos]
        for homonym in dic.homonyms(beg):
            parts = [*prev_parts, homonym]
            flag_sets = [w.flags for w in parts]
            compoundrules = [r for r in compoundrules if r.partial_match(flag_sets)]
            if compoundrules:
                by_rules = split_compound_by_rules(
                            aff, dic, word_rest[pos:],
                            compoundrules=compoundrules, prev_parts=parts
                        )
                for rest in by_rules:
                    yield [Paradigm(beg), *rest]
