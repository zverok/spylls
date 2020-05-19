from typing import Iterator, Set, Union, Tuple, cast
import itertools

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, permutations, suggest, ngram_suggest
import spyll.hunspell.algo.capitalization as cap


class Dictionary:
    def __init__(self, path):
        self.aff = readers.AffReader(path + '.aff')()
        self.dic = readers.DicReader(
            path + '.dic', encoding=self.aff.set, flag_format=self.aff.flag)()

    def roots(self, *, with_forbidden=False) -> Iterator[data.dic.Word]:
        for word in self.dic.words:
            if with_forbidden or self.aff.forbiddenword not in word.flags:
                yield word

    def forms_for(self, word: data.dic.Word, candidate: str):
        # word without prefixes/suffixes is also present...
        # TODO: unless it is forbidden :)
        res = [word.stem]

        suffixes = [
            suf
            for suf in self.aff.sfx
            if suf.flag in word.flags and word.stem.endswith(suf.strip) and candidate.endswith(suf.add)
        ]
        prefixes = [
            pref
            for pref in self.aff.pfx
            if pref.flag in word.flags and word.stem.startswith(pref.strip) and candidate.startswith(pref.add)
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

    def lookup(self, word: str) -> bool:
        return any(lookup.analyze(self.aff, self.dic, word))

    def lookup_nocap(self, word: str) -> bool:
        return any(lookup.analyze_nocap(self.aff, self.dic, word))

    def is_forbidden(self, word: str) -> bool:
        if not self.aff.forbiddenword:
            return False

        return any(self.aff.forbiddenword in w.flags for w in self.dic.homonyms(word))

    def suggest(self, word: str) -> Iterator[str]:
        yield from suggest.suggest(self, word)
