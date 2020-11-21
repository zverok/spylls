"""
The module represents data from Hunspell's ``*.dic`` file.

This text file has the following format:

.. code-block:: text

    124 # first line: number of entries

    # pseudo-comments are marked with "#"
    # Each entry has form:

    cat/ABC ph:kat

See :class:`Word` for explanation about fields.

The meaning of flags and data fields, as well as file encoding and other reading settings, are defined
by :class:`Aff <spyll.hunspell.data.aff.Aff>`.

:class:`Dic` contains all the entries (converted to ``Word``) from the ``*.dic`` file in the linear
list, and also provides some indexes and utilities for convenience.

``Dic`` is read by :meth:`read_dic <spyll.hunspell.readers.dic.read_dic>`.

``Dic``: list of entries
------------------------

.. autoclass:: Dic

``Word``: dictionary entry
--------------------------

.. autoclass:: Word
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import List, Set, Dict

from spyll.hunspell.algo.capitalization import Type as CapType
from spyll.hunspell.data.aff import Flag


@dataclass
class Word:
    """
    One word (stem) of a ``*.dic`` file.

    Each entry in the source contains something like:

    .. code-block:: text

        foo/ABC ph:phoo is:bar

    Where ``foo`` is the stem itself, ``ABC`` is word flags (flags meaning and format is defined by
    ``*.aff`` file), and ``ph:phoo is:bar`` are additional data tags (``ph`` is the tag and ``foo``
    is the value). Both flags and tags can be absent.

    Both flags and data tags can be also represented by numeric aliases defined in ``*.aff`` file,
    this is handled on reading stage, see :meth:`read_dic <spyll.hunspell.readers.dic.read_dic>` docs
    for details.

    **Attributes from source data:**

    .. autoattribute:: stem
    .. autoattribute:: flags
    .. autoattribute:: data

    **Attributes calculated on dictionary reading:**

    .. autoattribute:: alt_spellings
    .. autoattribute:: captype
    """

    #: Word stem
    stem: str
    #: Flags of the word, parsed depending on aff-file settings. ``ABCD`` might be parsed
    #: into ``{"A", "B", "C", "D"}`` (default flag format, "short"), or ``{"AB", "CD"}``
    #: ("long" flag format)
    flags: Set[str]
    #: Raw values of data tags. Each tag can be repeated several times, like ``witch ph:wich ph:which``,
    #: that's why dictionary values are lists
    data: Dict[str, List[str]]

    #: List of alternative word spellings, defined with ``ph:`` data tag, and
    #: used by :mod:`ngram_suggest <spyll.hunspell.algo.ngram_suggest>`. Not everythin specified
    #: with ``ph:`` is stored here, see :meth:`read_dic <spyll.hunspell.readers.dic.read_dic>` for
    #: details.
    alt_spellings: List[str]
    #: One of :class:`capitalization.Type <spyll.hunspell.algo.capitalization.Type>` (no capitalization,
    #: initial letter capitalized, all letters, or mixed) analyzed on dictionary reading, will be useful on lookup.
    captype: CapType

    def __repr__(self):
        return f"Word({self.stem} /{','.join(self.flags)})"


@dataclass
class Dic:
    """
    Represents list of words from ``*.dic`` file. Each word is stored as an instance of :class:`Word`.

    Besides flat list of all words, on initialization also creates word indexes, for regular search
    (``{stem => [Words]}``), and case-insensitive search (``{lowercased stem => [Words]}``).

    Note, that there could be (and typically are) several entries in the dictionary with same stems
    but different flags and/or data tags, that's why index values are lists of words. For example,
    in English dictionary "spell" (verb, related to reading/writing) and "spell" (noun, magical
    formula) may be different entries, defining different possible sets of suffixes and morphological
    properties.

    Typically, ``spyll`` user shouldn't create the instance of this class by themselves, it is
    created when the whole dictionary is read::

        dictionary = Dictionary.from_files('dictionaries/en_US')

        dictionary.dic  # instance of Dic

    **Data contents:**

    .. autoattribute:: words

    **Querying** (used by lookup and suggest):

    .. automethod:: homonyms
    .. automethod:: has_flag

    **Dictionary creation**

    .. automethod:: append
    """

    #: List of all words from ``*.dic`` file
    words: List[Word]

    def __post_init__(self):
        self.index = defaultdict(list)
        self.lowercase_index = defaultdict(list)

    def homonyms(self, stem: str, *, ignorecase: bool = False) -> List[Word]:
        """
        Returns all :class:`Word` instances with the same stem.

        Args:
            stem: Stem to search
            ignorecase: If passed, the stems are searched in the lowercased index (and the ``stem``
                        itself assumed to be lowercased). Used by lookup to find a correspondence
                        for uppercased word, if the stem has complex capitalization (find "McDonalds"
                        by "MCDONALDS")
        """
        if ignorecase:
            return self.lowercase_index.get(stem, [])
        return self.index.get(stem, [])

    def has_flag(self, stem: str, flag: Flag, *, for_all: bool = False) -> bool:
        """
        If any/all of the homonyms have specified flag. It is frequently necessary in lookup algo to
        check something like "...but if there is ANY dictionary entry with this stem and 'forbidden'
        flag...", or "...but if ALL dictionary entries with this stem marked as 'forbidden'..."
        """
        homonyms = self.homonyms(stem)
        if not homonyms:
            return False
        if for_all:
            return all(flag in homonym.flags for homonym in homonyms)
        return any(flag in homonym.flags for homonym in homonyms)

    def append(self, word: Word, *, lower: List[str]):
        """
        Used only by :meth:`read_dic <spyll.hunspell.readers.dic.read_dic>` to put the word into the
        dictionary.

        Args:
            word: The word instance, already pre-populated
            lower: List of all the lowercase forms of word stems. They are pre-calculated on dictionary
                   reading, because proper lowercasing requires casing context; and may produce several
                   lowercased variants (for German). See
                   :meth:`Casing.lower <spyll.hunspell.algo.capitalization.Casing.lower>` for details.
        """
        self.words.append(word)
        self.index[word.stem].append(word)
        for lword in lower:
            self.lowercase_index[lword].append(word)
