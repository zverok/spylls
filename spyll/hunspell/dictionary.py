import itertools

from dataclasses import dataclass
from typing import List
from enum import Enum

from spyll.hunspell.readers import AffReader, DicReader
from spyll.hunspell.algo import Stemmer
from spyll.hunspell.algo import compounder as cpd

Cap = Enum('Cap', 'NO INIT ALL HUHINIT HUH')

@dataclass
class FlagAnd:
    operands: List[str]

@dataclass
class FlagOr:
    operands: List[str]

@dataclass
class FlagNot:
    operand: str

def flags_match(statement, flags):
    if not statement or not flags:
        return True

    if type(statement) == FlagOr:
        return any([flags_match(o, flags) for o in statement.operands])
    elif type(statement) == FlagAnd:
        return all([flags_match(o, flags) for o in statement.operands])
    elif type(statement) == FlagNot:
        return not flags_match(statement.operand, flags)
    else: # just singular flag
        return statement in flags

def and_(*operands):
    operands = list(filter(None, operands))
    return None if not operands else FlagAnd(operands=operands)

def or_(*operands):
    operands = list(filter(None, operands))
    return None if not operands else FlagOr(operands=operands)

def not_(operand):
    return None if not operand else FlagNot(operand=operand)

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

class Dictionary:
    def __init__(self, path):
        self.aff = AffReader(path + '.aff')()
        self.dic = DicReader(path + '.dic', encoding = self.aff.set, flag_format = self.aff.flag)()
        self.stemmer = Stemmer(
            prefixes = self.aff.pfx,
            suffixes = self.aff.sfx,
            needaffix = self.aff.needaffix,
            compoundpermit = self.aff.compoundpermitflag,
            compoundforbid = self.aff.compoundforbidflag
        )
        self.compounder = cpd.Compounder(min_length = self.aff.compoundmin)

    def lookup(self, word):
        if self.forbiddenword(word):
            return []

        res = self._lookup(word)
        if not res:
            captype = guess_capitalization(word)
            # Capitalized: accept this form, and lowercase
            if captype == Cap.INIT:
                res = self._lookup(word.lower())
            elif captype == Cap.ALL:
                res = self._lookup(word.lower(), allcap=True)

        return res

    def _lookup(self, word, allcap=False):
        res = []
        for form in self._lookup_forms(word, allcap=allcap):
            res.append(form)

        for variant in self.compounder(word):
            # 3 strategies (could all exist at the same time! check HU):
            #
            # 1. COMPOUNDFLAG: this word can be in compound
            # 2. COMPOUNDBEG/MIDDLE/END
            # 3. COMPOUNDRULE: words with those flags make compounds
            forms = [self._lookup_forms(p.word, compoundpos=p.pos) for p in variant]
            for combination in itertools.product(*forms):
                res.append(combination)

        # print(res)
        return res

    def _lookup_forms(self, word, allcap=False, compoundpos=None):
        res = []
        # TODO: when compoundpos is present, only first word can have prefix, only last word
        # can have suffix (though, there ARE affixes allowed inside compounds by special flag)
        for form in self.stemmer(word, compoundpos=compoundpos):
            # print(form)
            for w in self.dic.words:
                found = w.stem == form.stem
                if allcap:
                    found = found or w.stem.lower() == form.stem.lower()
                if found and self._is_compatible(w, form, compoundpos=compoundpos):
                    res.append(form)

        return res

    def compounding_flags(self, form, compoundpos):
        if compoundpos == cpd.Pos.BEGIN:
            return or_(self.aff.compoundflag, self.aff.compoundbegin)
        elif compoundpos == cpd.Pos.END:
            return or_(self.aff.compoundflag, self.aff.compoundlast)
        elif compoundpos == cpd.Pos.MIDDLE:
            return or_(self.aff.compoundflag, self.aff.compoundmiddle)
        elif compoundpos is None:
            return not_(self.aff.onlyincompound)

    def affix_flags(self, form):
        if not form.suffix and not form.prefix:
            return and_(not_(self.aff.needaffix), not_(self.aff.pseudoroot))
        else:
            flags = []
            if form.suffix:
                flags.append(form.suffix.flag)
            if form.prefix:
                flags.append(form.prefix.flag)
            return and_(*flags)

    def forbiddenword(self, word):
        # print(word, self.aff.forbiddenword, self.dic.words)
        if not self.aff.forbiddenword:
            return False
        for w in self.dic.words:
            if w.stem == word and self.aff.forbiddenword in w.flags:
                return True
        return False

    def _is_compatible(self, dic_word, stem_form, compoundpos):
        # If affix is marked with some flag, it "poisons" the whole form: now it allows other
        # affixes
        all_flags = dic_word.flags.union(flags_of_affixes(stem_form))

        if not flags_match(self.compounding_flags(stem_form, compoundpos), all_flags):
            return False

        if not flags_match(self.affix_flags(stem_form), all_flags):
            return False

        return True

def flags_of_affixes(stem_form):
    res = []
    if stem_form.prefix:
        res.append(stem_form.prefix.flags)
    if stem_form.suffix:
        res.append(stem_form.suffix.flags)

    return set.union(*res) if res else set()
