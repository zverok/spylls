from typing import Iterator
import zipfile

from spyll.hunspell import data, readers
from spyll.hunspell.algo import lookup, suggest


class Dictionary:
    aff: data.Aff
    dic: data.Dic

    # .xpi, .odt
    @classmethod
    def from_zip(cls, path):
        zip = zipfile.ZipFile(path)
        # TODO: fail if there are several
        aff_path = [name for name in zip.namelist() if name.endswith('.aff')][0]
        dic_path = [name for name in zip.namelist() if name.endswith('.dic')][0]
        aff, context = readers.read_aff(zip.open(aff_path))
        dic = readers.read_dic(zip.open(dic_path), context=context)

        return cls(aff, dic)

    @classmethod
    def from_folder(cls, path):
        aff, context = readers.read_aff(path + '.aff')
        dic = readers.read_dic(path + '.dic', context=context)

        return cls(aff, dic)

    # TODO: from_system

    def __init__(self, aff, dic):
        self.aff = aff
        self.dic = dic

        self.lookuper = lookup.Lookup(self.aff, self.dic)
        self.suggester = suggest.Suggest(self.aff, self.dic, self.lookuper)

    def lookup(self, word: str, **kwarg) -> bool:
        return self.lookuper(word, **kwarg)

    def suggest(self, word: str) -> Iterator[str]:
        yield from self.suggester(word)
