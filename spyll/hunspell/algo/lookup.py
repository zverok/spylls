import itertools
import collections
from enum import Enum
from typing import List, Iterator, Union, Optional, Any

from spyll.hunspell import data

CompoundPos = Enum('CompoundPos', 'BEGIN MIDDLE END')

Cap = Enum('Cap', 'NO INIT ALL HUHINIT HUH')

Paradigm = collections.namedtuple('Paradigm',
    ['stem', 'prefix', 'suffix', 'prefix2', 'suffix2'],
    defaults=[None, None, None, None]
)

Compound = List[Paradigm]

def lookup(aff: data.Aff, dic: data.Dic, word: str) -> bool:
    return any(analyze(aff, dic, word))

def analyze(aff: data.Aff, dic: data.Dic, word: str) -> Iterator[Union[Paradigm, Compound]]:
    if aff.forbiddenword and any(aff.forbiddenword in w.flags for w in dic.homonyms(word)):
        return

    res = analyze_nocap(aff, dic, word)

    captype = guess_capitalization(word)

    # Capitalized: accept this form, and lowercase
    if captype == Cap.INIT:
        res = itertools.chain(res, analyze_nocap(aff, dic, word.lower()))
    elif captype == Cap.ALL:
        res = itertools.chain(res, analyze_nocap(aff, dic, word.lower(), allcap=True))

    return res

def analyze_nocap(aff: data.Aff, dic: data.Dic, word: str, allcap: bool = False) -> Iterator[Paradigm]:
    return itertools.chain(
        analyze_affixed(aff, dic, word, allcap = allcap),
        analyze_compound(aff, dic, word)
    )

def analyze_affixed(
    aff: data.Aff,
    dic: data.Dic,
    word: str,
    allcap: bool=False,
    compoundpos: Optional[CompoundPos]=None) -> Iterator[Paradigm]:

    for form in split_affixes(aff, word, compoundpos=compoundpos):
        found = False
        for w in dic.homonyms(form.stem):
            if have_compatible_flags(aff, w, form, compoundpos=compoundpos):
                found = True
                yield form

        if not found:
            for w in dic.homonyms(form.stem, ignorecase=True):
                if have_compatible_flags(aff, w, form, compoundpos=compoundpos): yield form

def analyze_compound(aff: data.Aff, dic: data.Dic, word: str) -> Iterator[Compound]:
    if aff.compoundbegin or aff.compoundflag:
        by_flags = split_compound_by_flags(aff, dic, word)
    else:
        by_flags = []

    if aff.compoundrules:
        by_rules = split_compound_by_rules(aff, dic, word, compoundrules=aff.compoundrules)
    else:
        by_rules = []

    return itertools.chain(by_flags, by_rules)


def have_compatible_flags(
    aff: data.Aff,
    dictionary_word: data.dic.Word,
    paradigm: Paradigm,
    compoundpos: CompoundPos) -> bool:

    all_flags = dictionary_word.flags
    if paradigm.prefix: all_flags = all_flags.union(paradigm.prefix.flags)
    if paradigm.suffix: all_flags = all_flags.union(paradigm.suffix.flags)

    # Check affix flags
    if not paradigm.suffix and not paradigm.prefix:
        if aff.needaffix and not aff.needaffix in all_flags: return False
        if aff.pseudoroot and not aff.pseudoroot in all_flags: return False

    if paradigm.prefix and not paradigm.prefix.flag in all_flags: return False
    if paradigm.suffix and not paradigm.suffix.flag in all_flags: return False

    # Check compound flags

    # FIXME: "neither of compounding flags present and we still try compound" will fail here,
    # but we shouldn't even try
    if compoundpos:
        if aff.compoundflag and aff.compoundflag in all_flags: return True

        if compoundpos == CompoundPos.BEGIN:
            if not aff.compoundbegin or not aff.compoundbegin in all_flags: return False
        elif compoundpos == CompoundPos.END:
            if not aff.compoundend or not aff.compoundend in all_flags: return False
        elif compoundpos == CompoundPos.MIDDLE:
            if not aff.compoundmiddle or not aff.compoundmiddle in all_flags: return False
    else:
        if aff.onlyincompound and not aff.onlyincompound in all_flags: return False

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
            if not only_affix_need_affix(r, aff.needaffix): yield r
    else:
        # FIXME: WTF???
        # return result
        for r in result: yield r

def _split_affixes(
    aff: data.Aff,
    word: str,
    compoundpos: Optional[CompoundPos] = None) -> Iterator[Paradigm]:

    yield Paradigm(word) # "Whole word" is always existing option

    for form in desuffix(aff, word, compoundpos=compoundpos):
        yield form

    for form in deprefix(aff, word, compoundpos=compoundpos):
        yield form

        if form.prefix.crossproduct:
            for form2 in desuffix(aff, form.stem, compoundpos=compoundpos):
                if form2.suffix.crossproduct:
                    yield form2._replace(prefix=form.prefix)

def desuffix(
    aff: data.Aff,
    word: str,
    extra_flag: Optional[str]=None,
    compoundpos: Optional[CompoundPos]=None) -> Iterator[Paradigm]:

    for stem, suf in _desuffix(aff, word, extra_flag=extra_flag, compoundpos=compoundpos):
        yield Paradigm(stem, suffix=suf)

        if not extra_flag: # only one level depth
            for form2 in desuffix(aff, stem, extra_flag=suf.flag, compoundpos=compoundpos):
                yield form2._replace(suffix2=suf)

def deprefix(
    aff: data.Aff,
    word: str,
    extra_flag: Optional[str]=None,
    compoundpos: Optional[CompoundPos]=None) -> Iterator[Paradigm]:

    for stem, pref in _deprefix(aff, word, extra_flag=extra_flag, compoundpos=compoundpos):
        yield Paradigm(stem, prefix=pref)
        if not extra_flag: # only one level depth
            for form2 in deprefix(aff, stem, extra_flag=pref.flag, compoundpos=compoundpos):
                yield form2._replace(prefix2=pref)

def _desuffix(
    aff: data.Aff,
    word: str,
    extra_flag: Optional[str]=None,
    compoundpos: Optional[CompoundPos]=None) -> Iterator[Paradigm]:

    if compoundpos is None or compoundpos == CompoundPos.END:
        checkpermit = False
    else:
        # No possibility any suffix will be OK
        if not aff.compoundpermitflag: return
        checkpermit = True

    for suf in aff.suffixes.lookup(word[::-1]):
        if extra_flag and not extra_flag in suf.flags: continue
        if checkpermit and not aff.compoundpermitflag in suf.flags: continue
        if compoundpos is not None and aff.compoundforbidflag in suf.flags: continue

        if suf.regexp.search(word):
            yield (suf.regexp.sub(suf.strip, word), suf)

def _deprefix(
    aff: data.Aff,
    word: str,
    extra_flag: Optional[str]=None,
    compoundpos: Optional[CompoundPos]=None) -> Iterator[Paradigm]:

    if compoundpos is None or compoundpos == CompoundPos.BEGIN:
        checkpermit = False
    else:
        # No possibility any prefix will be OK
        if not aff.compoundpermitflag: return
        checkpermit = True

    for pref in aff.prefixes.lookup(word):
        if extra_flag and not extra_flag in pref.flags: continue
        if checkpermit and not aff.compoundpermitflag in pref.flags: continue
        if compoundpos is not None and aff.compoundforbidflag in pref.flags: continue

        if pref.regexp.search(word):
            yield (pref.regexp.sub(pref.strip, word), pref)

def only_affix_need_affix(form, flag):
    all_affixes = list(filter(None, [form.prefix, form.prefix2, form.suffix, form.suffix2]))
    if not all_affixes: return False
    needaffs = [aff for aff in all_affixes if flag in aff.flags]
    return len(all_affixes) == len(needaffs)

# Compounding details
# -------------------

def split_compound_by_flags(
    aff: data.Aff,
    dic: data.Dic,
    word_rest: str,
    prev_parts: List[Paradigm] = []) -> Iterator[List[Paradigm]]:

    # If it is middle of compounding process "the rest of the word is the whole last part" is always
    # possible
    if prev_parts:
        for paradigm in analyze_affixed(aff, dic, word_rest, compoundpos=CompoundPos.END):
            yield [paradigm]

    if len(word_rest) < aff.compoundmin * 2 or \
        (aff.compoundwordsmax and len(prev_parts) >= aff.compoundwordsmax):
        return

    compoundpos = CompoundPos.BEGIN if not prev_parts else CompoundPos.MIDDLE

    for pos in range(aff.compoundmin, len(word_rest) - aff.compoundmin + 1):
        beg = word_rest[0:pos]

        for paradigm in analyze_affixed(aff, dic, beg, compoundpos=compoundpos):
            parts = [*prev_parts, paradigm]
            for rest in split_compound_by_flags(aff, dic, word_rest[pos:], parts):
                yield [paradigm, *rest]

def split_compound_by_rules(
    aff: data.Aff,
    dic: data.Dic,
    word_rest: str,
    compoundrules: List[Any],
    prev_parts: List[data.dic.Word] = []) -> Iterator[List[Paradigm]]:

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
                for rest in split_compound_by_rules(aff, dic, word_rest[pos:], compoundrules=compoundrules, prev_parts=parts):
                    yield [Paradigm(beg), *rest]

# Utility algorithms
# ------------------

def guess_capitalization(word):
    if word.lower() == word:
        return Cap.NO
    elif word[:1].lower() + word[1:] == word.lower():
        return Cap.INIT
    elif word.upper() == word:
        return Cap.ALL
    elif word[:1].lower() != word[:1]:
        return Cap.HUHINIT
    else:
        return Cap.HUH
