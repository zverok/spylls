from typing import Iterator

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, suggest


class Dictionary:
    def __init__(self, path):
        self.aff, context = readers.read_aff(path + '.aff')
        self.dic = readers.read_dic(path + '.dic', context=context)

        self.analyzer = lookup.Analyzer(self.aff, self.dic)

    def roots(self, *,
              with_forbidden=False,
              with_nosuggest=True,
              with_onlyincompound=True) -> Iterator[data.dic.Word]:

        for word in self.dic.words:
            if (with_forbidden or self.aff.FORBIDDENWORD not in word.flags) and \
               (with_nosuggest or self.aff.NOSUGGEST not in word.flags) and \
               (with_onlyincompound or self.aff.ONLYINCOMPOUND not in word.flags):
                yield word

    def lookup(self, word: str, *, capitalization=True, allow_nosuggest=True, allow_break=True) -> bool:
        return self.analyzer.lookup(word, capitalization=capitalization, allow_nosuggest=allow_nosuggest, allow_break=allow_break)

    def is_forbidden(self, word: str) -> bool:
        if not self.aff.FORBIDDENWORD:
            return False

        return self.dic.has_flag(word, self.aff.FORBIDDENWORD)

    def keepcase(self, word: str) -> bool:
        if not self.aff.KEEPCASE:
            return False

        return self.dic.has_flag(word, self.aff.KEEPCASE)

    def suggest(self, word: str) -> Iterator[str]:
        yield from suggest.suggest(self, word)

    def suffixes_for(self, word):
        res = []
        for flag in word.flags:
            if flag in self.aff.SFX:
                for suf in self.aff.SFX[flag]:
                    if suf.cond_regexp.search(word.stem):
                        res.append(suf)
                        break
        return res

    def prefixes_for(self, word):
        res = []
        for flag in word.flags:
            if flag in self.aff.PFX:
                for pref in self.aff.PFX[flag]:
                    if pref.cond_regexp.search(word.stem):
                        res.append(pref)
                        break
        return res

    def forms_for(self, word: data.dic.Word, candidate: str):
        # word without prefixes/suffixes is also present...
        # TODO: unless it is forbidden :)
        res = [word.stem]

        suffixes = [
            suf
            for suf in self.suffixes_for(word)
            if candidate.endswith(suf.add)
        ]
        prefixes = [
            pref
            for pref in self.prefixes_for(word)
            if candidate.startswith(pref.add)
        ]

        for suf in suffixes:
            root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
            res.append(root + suf.add)

        for suf in suffixes:
            if not suf.crossproduct:
                continue
            root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
            for pref in prefixes:
                if not pref.crossproduct:
                    continue
                root = root[len(pref.strip):]
                res.append(pref.add + root + suf.add)

        for pref in prefixes:
            root = word.stem[len(pref.strip):]
            res.append(pref.add + root)

        return res
