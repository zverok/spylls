from typing import Iterator, Set, Union, Tuple, cast

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, permutations, ngram_suggest
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

    def forms_for(self, word: data.dic.Word):
        # word without prefixes/suffixes is also present...
        # TODO: unless it is forbidden :)
        res = [word.stem]

        suffixes = [
            suf
            for suf in self.aff.sfx
            if suf.flag in word.flags and word.stem.endswith(suf.strip)
        ]
        prefixes = [
            pref
            for pref in self.aff.pfx
            if pref.flag in word.flags and word.stem.startswith(pref.strip)
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

    def suggest(self, word: str) -> Iterator[str]:
        captype, variants = cap.variants(word)
        found = False
        seen = set()

        def handle_found(suggestion):
            cased_suggestion = cap.coerce(suggestion, captype)
            if suggestion != cased_suggestion and self.is_forbidden(cased_suggestion):
                cased_suggestion = suggestion
            if cased_suggestion not in seen:
                seen.add(cased_suggestion)
                return cased_suggestion
            else:
                return None

        for variant in variants:
            for sug in self.suggest_permute(variant):
                sug = handle_found(sug)
                if sug:
                    found = True
                    yield sug

        if found or self.aff.maxngramsugs == 0:
            return

        ngramsugs = 0
        for variant in variants:
            for sug in ngram_suggest.ngram_suggest(
                        self, word, maxdiff=self.aff.maxdiff, onlymaxdiff=self.aff.onlymaxdiff):
                sug = handle_found(sug)
                if sug:
                    yield sug
                    ngramsugs += 1
                    if ngramsugs >= self.aff.maxngramsugs:
                        break


    def is_forbidden(self, word: str) -> bool:
        if not self.aff.forbiddenword:
            return False

        return any(self.aff.forbiddenword in w.flags for w in self.dic.homonyms(word))


    def suggest_permute(self, word: str) -> Iterator[str]:
        seen: Set[Union[str, Tuple[str, str]]] = set()
        found = False

        for sug in permutations.splitword(word, use_dash=self.aff.use_dash()):
            if sug not in seen:
                seen.add(sug)
                if self.lookup_nocap(sug):
                    yield sug
                    found = True

        if found:
            return

        for sug2 in permutations.permutations(word, self.aff):
            if tuple(sug2) not in seen:
                seen.add(tuple(sug2))
                if type(sug2) is list:
                    if all(self.lookup_nocap(s) for s in sug2):
                        yield ' '.join(sug2)
                        if self.aff.use_dash():
                            yield '-'.join(sug2)
                        found = True
                elif type(sug2) is str:
                    if self.lookup_nocap(cast(str, sug2)):
                        yield sug2
                        found = True
