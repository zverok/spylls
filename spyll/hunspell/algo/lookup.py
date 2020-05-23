import itertools
import collections
from enum import Enum
from typing import List, Iterator, Union, Optional, Tuple

from spyll.hunspell import data
import spyll.hunspell.algo.capitalization as cap

CompoundPos = Enum('CompoundPos', 'BEGIN MIDDLE END')

Paradigm = collections.namedtuple('Paradigm',
                                  ['stem', 'prefix', 'suffix', 'prefix2', 'suffix2'],
                                  defaults=[None, None, None, None]
                                  )

Compound = List[Paradigm]


def analyze(aff: data.Aff, dic: data.Dic, word: str, *, allow_nosuggest=True) -> Iterator[Union[Paradigm, Compound]]:
    res = analyze_nocap(aff, dic, word)

    captype = cap.guess(word)

    # Capitalized: accept this form, and lowercase
    if captype == cap.Cap.INIT:
        res = itertools.chain(res, analyze_nocap(aff, dic, word.lower(), allow_nosuggest=allow_nosuggest))
    elif captype == cap.Cap.ALL:
        res = itertools.chain(res, analyze_nocap(aff, dic, word.lower(), allcap=True, allow_nosuggest=allow_nosuggest))

    return res


def analyze_nocap(
        aff: data.Aff,
        dic: data.Dic,
        word: str,
        *,
        allcap: bool = False,
        allow_nosuggest=True) -> Iterator[Union[Paradigm, Compound]]:

    if aff.forbiddenword and any(aff.forbiddenword in w.flags for w in dic.homonyms(word)):
        return iter(())

    return itertools.chain(
        analyze_affixed(aff, dic, word, allcap=allcap, allow_nosuggest=allow_nosuggest),
        analyze_compound(aff, dic, word, allow_nosuggest=allow_nosuggest)
    )


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
            if have_compatible_flags(aff, w, form, compoundpos=compoundpos, allow_nosuggest=allow_nosuggest):
                found = True
                yield form

        if not found:
            for w in dic.homonyms(form.stem, ignorecase=True):
                # If the dictionary word is not lowercase, we accept only exactly that
                # case (above), or ALLCAPS
                if not allcap and cap.guess(w.stem) != cap.Cap.NO:
                    continue
                if have_compatible_flags(aff, w, form, compoundpos=compoundpos, allow_nosuggest=allow_nosuggest):
                    yield form


def analyze_compound(aff: data.Aff, dic: data.Dic, word: str, allow_nosuggest=True) -> Iterator[Compound]:
    if aff.compoundbegin or aff.compoundflag:
        by_flags = split_compound_by_flags(aff, dic, word, allow_nosuggest=allow_nosuggest)
    else:
        by_flags = iter(())

    if aff.compoundrules:
        by_rules = split_compound_by_rules(aff, dic, word, compoundrules=aff.compoundrules, allow_nosuggest=allow_nosuggest)
    else:
        by_rules = iter(())

    return itertools.chain(by_flags, by_rules)


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

    if aff.forbiddenword and aff.forbiddenword in dictionary_word.flags:
        return False

    if not allow_nosuggest and aff.nosuggest and aff.nosuggest in dictionary_word.flags:
        return False

    # Check affix flags
    if not paradigm.suffix and not paradigm.prefix:
        if aff.needaffix and aff.needaffix in all_flags:
            return False
        if aff.pseudoroot and aff.pseudoroot in all_flags:
            return False

    if paradigm.prefix and paradigm.prefix.flag not in all_flags:
        return False
    if paradigm.suffix and paradigm.suffix.flag not in all_flags:
        return False

    # Check compound flags

    # FIXME: "neither of compounding flags present and we still try compound" will fail here,
    # but we shouldn't even try
    if compoundpos:
        if aff.compoundflag and aff.compoundflag in all_flags:
            return True

        if compoundpos == CompoundPos.BEGIN:
            if not aff.compoundbegin or aff.compoundbegin not in all_flags:
                return False
        elif compoundpos == CompoundPos.END:
            if not aff.compoundlast or aff.compoundlast not in all_flags:
                return False
        elif compoundpos == CompoundPos.MIDDLE:
            if not aff.compoundmiddle or aff.compoundmiddle not in all_flags:
                return False
    else:
        if aff.onlyincompound and aff.onlyincompound in all_flags:
            return False

    return True


# Affixes-related algorithms
# --------------------------


def split_affixes(
        aff: data.Aff,
        word: str,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    result = _split_affixes(aff, word, compoundpos=compoundpos)

    if aff.needaffix:
        for r in result:
            if not only_affix_need_affix(r, aff.needaffix):
                yield r
    else:
        yield from result


def _split_affixes(
        aff: data.Aff,
        word: str,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    yield Paradigm(word)    # "Whole word" is always existing option

    yield from desuffix(aff, word, compoundpos=compoundpos)

    for form in deprefix(aff, word, compoundpos=compoundpos):
        yield form

        if form.prefix.crossproduct:
            for form2 in desuffix(aff, form.stem, compoundpos=compoundpos):
                if form2.suffix.crossproduct:
                    yield form2._replace(prefix=form.prefix)


def desuffix(
        aff: data.Aff,
        word: str,
        extra_flag: Optional[str] = None,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    for stem, suf in _desuffix(aff, word, extra_flag=extra_flag, compoundpos=compoundpos):
        yield Paradigm(stem, suffix=suf)

        if not extra_flag:  # only one level depth
            for form2 in desuffix(aff, stem, extra_flag=suf.flag, compoundpos=compoundpos):
                yield form2._replace(suffix2=suf)


def deprefix(
        aff: data.Aff,
        word: str,
        extra_flag: Optional[str] = None,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    for stem, pref in _deprefix(aff, word, extra_flag=extra_flag, compoundpos=compoundpos):
        yield Paradigm(stem, prefix=pref)

        # TODO: Only if compoundpreffixes are allowed in *.aff
        if not extra_flag:  # only one level depth
            for form2 in deprefix(aff, stem, extra_flag=pref.flag, compoundpos=compoundpos):
                yield form2._replace(prefix2=pref)


def _desuffix(
        aff: data.Aff,
        word: str,
        extra_flag: Optional[str] = None,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Tuple[str, data.aff.Suffix]]:

    if compoundpos is None or compoundpos == CompoundPos.END:
        checkpermit = False
    else:
        # No possibility any suffix will be OK
        if not aff.compoundpermitflag:
            return
        checkpermit = True

    for _, suf in aff.suffixes.prefixes(word[::-1]):
        if extra_flag and extra_flag not in suf.flags:
            continue
        if checkpermit and aff.compoundpermitflag not in suf.flags:
            continue
        if compoundpos is not None and aff.compoundforbidflag in suf.flags:
            continue

        if suf.regexp.search(word):
            yield (suf.regexp.sub(suf.strip, word), suf)


def _deprefix(
        aff: data.Aff,
        word: str,
        extra_flag: Optional[str] = None,
        compoundpos: Optional[CompoundPos] = None) -> Iterator[Tuple[str, data.aff.Prefix]]:

    if compoundpos is None or compoundpos == CompoundPos.BEGIN:
        checkpermit = False
    else:
        # No possibility any prefix will be OK
        if not aff.compoundpermitflag:
            return
        checkpermit = True

    for _, pref in aff.prefixes.prefixes(word):
        if extra_flag and extra_flag not in pref.flags:
            continue
        if checkpermit and aff.compoundpermitflag not in pref.flags:
            continue
        if compoundpos is not None and aff.compoundforbidflag in pref.flags:
            continue

        if pref.regexp.search(word):
            yield (pref.regexp.sub(pref.strip, word), pref)


def only_affix_need_affix(form, flag):
    all_affixes = list(filter(None, [form.prefix, form.prefix2, form.suffix, form.suffix2]))
    if not all_affixes:
        return False
    needaffs = [aff for aff in all_affixes if flag in aff.flags]
    return len(all_affixes) == len(needaffs)

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
        for paradigm in analyze_affixed(aff, dic, word_rest, compoundpos=CompoundPos.END, allow_nosuggest=allow_nosuggest):
            yield [paradigm]

    if len(word_rest) < aff.compoundmin * 2 or \
            (aff.compoundwordsmax and len(prev_parts) >= aff.compoundwordsmax):
        return

    compoundpos = CompoundPos.BEGIN if not prev_parts else CompoundPos.MIDDLE

    for pos in range(aff.compoundmin, len(word_rest) - aff.compoundmin + 1):
        beg = word_rest[0:pos]

        for paradigm in analyze_affixed(aff, dic, beg, compoundpos=compoundpos, allow_nosuggest=allow_nosuggest):
            parts = [*prev_parts, paradigm]
            for rest in split_compound_by_flags(aff, dic, word_rest[pos:], parts, allow_nosuggest=allow_nosuggest):
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
