from typing import List, Iterator, Set, Union, Tuple, cast

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, permutations, ngram_suggest

class Dictionary:
    def __init__(self, path):
        self.aff = readers.AffReader(path + '.aff')()
        self.dic = readers.DicReader(path + '.dic', encoding = self.aff.set, flag_format = self.aff.flag)()

    def roots(self, *, with_forbidden=False) -> Iterator[data.dic.Word]:
        for word in self.dic.words:
            if with_forbidden or not self.aff.forbiddenword in word.flags:
                yield word

    def forms_for(self, word: data.dic.Word):
        # word without prefixes/suffixes is also present...
        # TODO: unless it is forbidden :)
        res = [word.stem]

        suffixes = [suf for suf in self.aff.sfx if suf.flag in word.flags and word.stem.endswith(suf.strip)]
        prefixes = [pref for pref in self.aff.pfx if pref.flag in word.flags and word.stem.startswith(pref.strip)]

        for suf in suffixes:
            root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
            res.append(root + suf.add)

        for suf in suffixes:
            if not suf.crossproduct: continue
            root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
            for pref in prefixes:
                if not pref.crossproduct: continue
                root = root[len(pref.strip):]
                res.append(pref.add + root + suf.add)

        for pref in prefixes:
            root = word.stem[len(pref.strip):]
            res.append(pref.add + root)

        return res

    def lookup(self, word: str) -> bool:
        return any(lookup.analyze(self.aff, self.dic, word))

    def suggest(self, word: str) -> Iterator[Union[str, Tuple[str, str]]]:
        seen: Set[Union[str, Tuple[str, str]]] = set()
        found = False

        for sug in permutations.splitword(word, use_dash=self.aff.use_dash()):
            if not sug in seen:
                seen.add(sug)
                if self.lookup(sug):
                    yield sug
                    found = True

        if found: return

        for sug2 in permutations.permutations(word, self.aff):
            if not sug2 in seen:
                seen.add(sug2)
                if type(sug2) is tuple:
                    if all(self.lookup(s) for s in sug2):
                        yield ' '.join(sug2)
                        if self.aff.use_dash():
                            yield '-'.join(sug2)
                        found = True
                elif type(sug2) is str:
                    if self.lookup(cast(str, sug2)):
                        yield sug2
                        found = True

        if found: return

        for sug in ngram_suggest.ngram_suggest(self, word, maxdiff=self.aff.maxdiff, onlymaxdiff=self.aff.onlymaxdiff):
            if not sug in seen:
                    yield sug
                    seen.add(sug)
