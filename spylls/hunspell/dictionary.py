from __future__ import annotations

import glob
import zipfile

from typing import Iterator

from spylls.hunspell import data, readers
from spylls.hunspell.readers.file_reader import FileReader, ZipReader
from spylls.hunspell.algo import lookup, suggest


class Dictionary:
    """
    The main and only interface to ``spylls.hunspell`` as a library.

    Usage::

        from spylls.hunspell import Dictionary

        # from folder where en_US.aff and en_US.dic are present
        dictionary = Dictionary.from_files('/path/to/dictionary/en_US')
        # or, from Firefox/LibreOffice dictionary extension
        dictionary = Dictionary.from_zip('/path/to/dictionary/en_US.odt')
        # or, from system folders (on Linux)
        dictionary = Dictionary.from_system('en_US')

        print(dictionary.lookup('spylls'))
        # False
        for suggestion in dictionary.suggest('spylls'):
            print(sugestion)
        # spells
        # spills

    Internal algorithm implementations :attr:`lookuper` and :attr:`suggester` are exposed in order
    to allow experimenting with the implementation::

        # Produce all ways this word might be analysed by current dictionary
        for form in dictionary.lookuper.good_forms('building'):
            print(form)

        # AffixForm(building = building)
        # AffixForm(building = build + Suffix(ing: G×, on [[^e]]$))

        # Internal suggest method, showing information about suggestion method
        for suggestion in dictionary.suggester.suggest_internal('spylls'):
            print(suggestion)

        # Suggestion[badchar](spells)
        # Suggestion[badchar](spills)

    **Dictionary creation**

    .. automethod:: from_files
    .. automethod:: from_zip
    .. automethod:: from_system

    **Dictionary usage**

    .. automethod:: lookup
    .. automethod:: suggest

    **Data objects**

    .. autoattribute:: aff
    .. autoattribute:: dic

    **Algorithms**

    .. autoattribute:: lookuper
    .. autoattribute:: suggester
    """

    #: Contents of ``*.aff``
    aff: data.aff.Aff
    #: Contents of ``*.dic``
    dic: data.dic.Dic

    #: Instance of ``Lookup``, can be used for experimenting, see :mod:`algo.lookup <spylls.hunspell.algo.lookup>`.
    lookuper: lookup.Lookup
    #: Instance of ``Suggest``, can be used for experimenting, see :mod:`algo.suggest <spylls.hunspell.algo.suggest>`.
    suggester: suggest.Suggest

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
    def from_files(cls, path: str) -> Dictionary:
        """
        Read dictionary from pair of files ``/some/path/some_name.aff`` and ``/some/path/some_name.dic``.

        Args:
            path: Should be just ``/some/path/some_name``.
        """

        aff, context = readers.read_aff(FileReader(path + '.aff'))
        dic = readers.read_dic(FileReader(path + '.dic', encoding=context.encoding), aff=aff, context=context)

        return cls(aff, dic)

    # .xpi, .odt
    @classmethod
    def from_zip(cls, path: str) -> Dictionary:
        """
        Read dictionary from zip-archive containing ``*.aff`` and ``*.dic`` path. Note that Open/Libre
        Office dictionary extensions (``*.odt``) and Firefox/Thunderbird dictionary extensions (``*.xpi``)
        are in fact such archives, so ``Dictionary`` can be read from them without unpacking.

        Args:
            path: Path to zip-file/extension.
        """

        file = zipfile.ZipFile(path)
        # TODO: fail if there are several
        aff_path = [name for name in file.namelist() if name.endswith('.aff')][0]
        dic_path = [name for name in file.namelist() if name.endswith('.dic')][0]
        aff, context = readers.read_aff(ZipReader(file.open(aff_path)))
        dic = readers.read_dic(ZipReader(file.open(dic_path), encoding=context.encoding), aff=aff, context=context)

        return cls(aff, dic)

    @classmethod
    def from_system(cls, name: str) -> Dictionary:
        """
        Tries to find ``<name>.aff`` and ``<name>.dic`` on system paths known to store Hunspell dictionaries.
        Probably works only on Linux.

        Args:
            name: Language/dictionary name, like ``en_US``
        """

        for folder in cls.PATHES:
            pathes = glob.glob(f'{folder}/{name}.aff')
            if pathes:
                return cls.from_files(pathes[0].replace('.aff', ''))

        raise LookupError(f'{name}.aff not found (search pathes are {cls.PATHES!r})')

    def __init__(self, aff, dic):
        self.aff = aff
        self.dic = dic

        self.lookuper = lookup.Lookup(self.aff, self.dic)
        self.suggester = suggest.Suggest(self.aff, self.dic, self.lookuper)

    def lookup(self, word: str) -> bool:
        """
        Checks if the word is correct.

        ::

            >>> dictionary.lookup('spylls')
            False
            >>> dictionary.lookup('spells')
            True

        Args:
            word: Word to check
        """

        return self.lookuper(word)

    def suggest(self, word: str) -> Iterator[str]:
        """
        Suggests corrections for the misspelled word (in order of probability/similarity, best
        suggestions first), returns lazy generator of suggestions.

        ::

            >>> suggestions = dictionary.suggest('spylls')
            <generator object Dictionary.suggest at 0x7f5c63e4a2d0>

            >>> for suggestion in dictionary.suggest('spylls'):
            ...    print(sugestion)
            spells
            spills

        Args:
            word: Misspelled word
        """

        yield from self.suggester(word)
