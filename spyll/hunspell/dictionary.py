import glob
import zipfile

from typing import Iterator

from spyll.hunspell import data, readers
from spyll.hunspell.readers.file_reader import FileReader, ZipReader
from spyll.hunspell.algo import lookup, suggest


class Dictionary:
    aff: data.Aff
    dic: data.Dic

    # TODO: Firefox dictionaries path
    # TODO: Windows pathes
    PATHES = [
        # lib
        "/usr/share/hunspell",
        "/usr/share/myspell",
        "/usr/share/myspell/dicts",
        "/Library/Spelling",

        # OpenOffice
        "/opt/openoffice.org/basis3.0/share/dict/ooo",
        "/usr/lib/openoffice.org/basis3.0/share/dict/ooo",
        "/opt/openoffice.org2.4/share/dict/ooo",
        "/usr/lib/openoffice.org2.4/share/dict/ooo",
        "/opt/openoffice.org2.3/share/dict/ooo",
        "/usr/lib/openoffice.org2.3/share/dict/ooo",
        "/opt/openoffice.org2.2/share/dict/ooo",
        "/usr/lib/openoffice.org2.2/share/dict/ooo",
        "/opt/openoffice.org2.1/share/dict/ooo",
        "/usr/lib/openoffice.org2.1/share/dict/ooo",
        "/opt/openoffice.org2.0/share/dict/ooo",
        "/usr/lib/openoffice.org2.0/share/dict/ooo"
    ]

    @classmethod
    def from_files(cls, path):
        aff, context = readers.read_aff(FileReader(path + '.aff'))
        dic = readers.read_dic(FileReader(path + '.dic', encoding=context.encoding), context=context)

        return cls(aff, dic)

    # .xpi, .odt
    @classmethod
    def from_zip(cls, path):
        zip = zipfile.ZipFile(path)
        # TODO: fail if there are several
        aff_path = [name for name in zip.namelist() if name.endswith('.aff')][0]
        dic_path = [name for name in zip.namelist() if name.endswith('.dic')][0]
        aff, context = readers.read_aff(ZipReader(zip.open(aff_path)))
        dic = readers.read_dic(ZipReader(zip.open(dic_path), encoding=context.encoding), context=context)

        return cls(aff, dic)

    @classmethod
    def from_system(cls, name):
        for folder in cls.PATHES:
            pathes = glob.glob(f'{folder}/{name}.aff')
            if pathes:
                return cls.from_files(pathes[0].replace('.aff', ''))

    def __init__(self, aff, dic):
        self.aff = aff
        self.dic = dic

        self.lookuper = lookup.Lookup(self.aff, self.dic)
        self.suggester = suggest.Suggest(self.aff, self.dic, self.lookuper)

    def lookup(self, word: str, **kwarg) -> bool:
        return self.lookuper(word, **kwarg)

    def suggest(self, word: str) -> Iterator[str]:
        yield from self.suggester(word)
