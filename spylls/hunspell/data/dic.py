"""
The module represents data from Hunspell's ``*.dic`` file.

This text file has the following format:

.. code-block:: text

    124 # first line: number of entries

    # pseudo-comments are marked with "#"
    # Each entry has form:

    cat/ABC ph:kat

See :class:`Word` for explanation about fields.

The meaning of flags, as well as file encoding and other reading settings, are defined
by :class:`Aff <spylls.hunspell.data.aff.Aff>`.

:class:`Dic` contains all the entries (converted to ``Word``) from the ``*.dic`` file in the linear
list, and also provides some indexes and utilities for convenience.

``Dic`` is read by :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>`.

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

from spylls.hunspell.algo.capitalization import Type as CapType


@dataclass
class Word:
    """
    One word (stem) of a .dic file.

    Each entry in the source contains something like:

    .. code-block:: text

        foo/ABC ph:phoo is:bar

    Where ``foo`` is the stem itself, ``ABC`` is word flags (flags meaning and format is defined by
    ``*.aff`` file), and ``ph:phoo is:bar`` are additional data tags (``ph`` is the tag and ``foo``
    is the value). Both flags and tags can be absent.

    Both flags and data tags can be also represented by numeric aliases defined in .aff file
    (see :attr:`Aff.AF <spylls.hunspell.aff.Aff.AF>` and :attr:`Aff.AM <spylls.hunspell.aff.Aff.AM>`),
    this is handled on reading stage, see :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>` docs
    for details.

    Meaning of data tags are discussed in `hunspell docs
    <https://manpages.debian.org/experimental/libhunspell-dev/hunspell.5.en.html#Optional_data_fields>`_.
    Spylls, for now, provides special handling only for ``ph:`` field. The code probably means
    "phonetic", but the idea is that this field contains "alternative spellings" (or, rather, common
    misspellings) of the word. The simplest example is

    .. code-block:: text

        which ph:wich

    This specifies that dictionary word ``which`` is frequently misspelled as ``wich``, and would be
    considered in :class:`Suggest <spylls.hunspell.algo.suggest.Suggest>`. More complicated forms:

    .. code-block:: text

        pretty ph:prity*
        happy ph:hepi->happi

    The first one means "any ``prit`` inside word should be replaced by ``pret`` (chomping off
    the last letter of both), the second: "any ``hepi`` should be replaced to ``happi``, but we
    store this fact with stem ``happy``" (think "hepiness -> happiness").

    First (simple) form is stored in :attr:`alt_spellings` and used in
    :mod:`ngram_suggest <spylls.hunspell.algo.ngram_suggest>`,
    more complex forms are processed at reading stage and is actually stored in
    :attr:`Aff.REP <spylls.hunspell.data.aff.Aff.REP>`.

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
    #: used by :mod:`ngram_suggest <spylls.hunspell.algo.ngram_suggest>`. Not everythin specified
    #: with ``ph:`` is stored here, see expanations in class docs.
    alt_spellings: List[str]
    #: One of :class:`capitalization.Type <spylls.hunspell.algo.capitalization.Type>` (no capitalization,
    #: initial letter capitalized, all letters, or mixed) analyzed on dictionary reading, will be useful on lookup.
    captype: CapType

    def __repr__(self):
        return f"Word({self.stem} /{','.join(self.flags)})"


@dataclass
class Dic:
    """
    Represents list of words from ``*.dic`` file. Each word is stored as an instance of :class:`Word`.

    Besides flat list of all words, on initialization also creates word indexes, see :attr:`index`
    and :attr:`lowercase_index`.

    Note, that there could be (and typically are) several entries in the dictionary with same stems
    but different flags and/or data tags, that's why index values are lists of words. For example,
    in English dictionary "spell" (verb, related to reading/writing) and "spell" (noun, magical
    formula) may be different entries, defining different possible sets of suffixes and morphological
    properties.

    Typically, ``spylls`` user shouldn't create the instance of this class by themselves, it is
    created when the whole dictionary is read::

        >>> dictionary = Dictionary.from_files('dictionaries/en_US')

        >>> dictionary.dic
        Dictionary(... 62119 words ...)

        >>> dictionary.dic.homonyms('spell')
        [Word(spell /G,R,S,J,Z,D)]

    **Data contents:**

    .. autoattribute:: words

    .. py:attribute:: index
        :type: Dict[str, List[Word]]

        All .dic file entries for some stem.

    .. py:attribute:: lowercase_index
        :type: Dict[str, List[Word]]

        All .dic file entries for lowercase version of some stem.

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

    def has_flag(self, stem: str, flag: str, *, for_all: bool = False) -> bool:
        """
        If any/all of the homonyms have specified flag. It is frequently necessary in lookup algo to
        check something like "...but if there is ANY dictionary entry with this stem and 'forbidden'
        flag...", or "...but if ALL dictionary entries with this stem marked as 'forbidden'..."

        Args:
            stem: Stem present in dictionary
            flag: Flag to test
            for_all: If ``True``, checks if **all** homonyms have this flag, if ``False``, checks if
                     at least one.
        """
        homonyms = self.homonyms(stem)
        if not homonyms:
            return False
        if for_all:
            return all(flag in homonym.flags for homonym in homonyms)
        return any(flag in homonym.flags for homonym in homonyms)

    def append(self, word: Word, *, lower: List[str]):
        """
        Used only by :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>` to put the word into the
        dictionary.

        Args:
            word: The word instance, already pre-populated
            lower: List of all the lowercase forms of word stems. They are pre-calculated on dictionary
                   reading, because proper lowercasing requires casing context; and may produce several
                   lowercased variants (for German). See
                   :meth:`Casing.lower <spylls.hunspell.algo.capitalization.Casing.lower>` for details.
        """
        self.words.append(word)
        self.index[word.stem].append(word)
        for lword in lower:
            self.lowercase_index[lword].append(word)

    def __repr__(self):
        return f'Dictionary(... {len(self.words)} words ...)'
