from typing import Iterator

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, suggest


class Dictionary:
    def __init__(self, path):
        self.aff, context = readers.read_aff(path + '.aff')
        self.dic = readers.read_dic(path + '.dic', context=context)

        self.analyzer = lookup.Analyzer(self.aff, self.dic)
        self.suggester = suggest.Suggest(self.aff, self.dic, self.analyzer)

    def lookup(self, word: str, **kwarg) -> bool:
        return self.analyzer.lookup(word, **kwarg)

    def is_forbidden(self, word: str) -> bool:
        if not self.aff.FORBIDDENWORD:
            return False

        return self.dic.has_flag(word, self.aff.FORBIDDENWORD)

    def keepcase(self, word: str) -> bool:
        if not self.aff.KEEPCASE:
            return False

        return self.dic.has_flag(word, self.aff.KEEPCASE)

    def suggest(self, word: str) -> Iterator[str]:
        yield from self.suggester.suggest(word)
