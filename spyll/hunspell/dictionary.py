from typing import Iterator

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, suggest


class Dictionary:
    def __init__(self, path):
        self.aff = readers.AffReader(path + '.aff')()
        self.dic = readers.DicReader(
            path + '.dic', encoding=self.aff.set, flag_format=self.aff.flag)()

    def roots(self, *, with_forbidden=False, with_nosuggest=True) -> Iterator[data.dic.Word]:
        for word in self.dic.words:
            if with_forbidden or self.aff.forbiddenword not in word.flags and \
                with_nosuggest or self.aff.nosuggest not in word.flags:
                yield word

    def lookup(self, word: str, *, allow_nosuggest=True) -> bool:
        return any(lookup.analyze(self.aff, self.dic, word, allow_nosuggest=allow_nosuggest))

    def lookup_nocap(self, word: str, *, allow_nosuggest=True) -> bool:
        return any(lookup.analyze_nocap(self.aff, self.dic, word, allow_nosuggest=allow_nosuggest))

    def is_forbidden(self, word: str) -> bool:
        if not self.aff.forbiddenword:
            return False

        return any(self.aff.forbiddenword in w.flags for w in self.dic.homonyms(word))

    def suggest(self, word: str) -> Iterator[str]:
        yield from suggest.suggest(self, word)

    def suffixes_for(self, word):
        res = []
        for flag in word.flags:
            if flag in self.aff.sfx:
                for suf in self.aff.sfx[flag]:
                    if suf.cond_regexp.search(word.stem):
                        res.append(suf)
                        break
        return res

    def prefixes_for(self, word):
        res = []
        for flag in word.flags:
            if flag in self.aff.pfx:
                for pref in self.aff.pfx[flag]:
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
