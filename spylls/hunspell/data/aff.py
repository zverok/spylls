"""
The module represents data from Hunspell's ``*.aff`` file.

This text file has the following format:

.. code-block:: text

    # pseudo-comment
    DIRECTIVE_NAME value1 value2 value 3

    # directives with large array of values
    DIRECTIVE_NAME <num_of_values>
    DIRECTIVE_NAME value1_1 value1_2 value1_3
    DIRECTIVE_NAME value2_1 value2_2 value2_3
    # ...

How many values should be after ``DIRECTIVE_NAME``, is defined by directive itself. Values are separated
by any number of spaces (so, if some values should include literal " ", they encode it as "_").

    *Note:* We are saying "pseudo-comment" above, because it is just a convention. In fact, Hunspell has
    no code explicitly interpreting anything starting with ``#`` as a comment -- it is rather ignores everything
    that is not known directive name, and everything after expected number of directive values. But it is
    important NOT to drop ``#`` and content after it before interpreting, as it might be meaningful!
    Some dictionaries define ``#`` to be a flag, or a ``BREAK`` character. For example ``en_GB`` in
    LibreOffice does this:

    .. code-block:: text

        # in .aff file:
        COMPOUNDRULE #*0{
        # reads: rule of producing compound words:
        #  any words with flag "#", 0 or more times (*),
        #  then any word with flag "0",
        #  then any word with flag "{"

        # in .dic file:
        1/#0
        # reads: "1" is a word, having flags "#" and "0"

The :class:`Aff` class stores all data from the the file — read class docs to better understand the
conventions and usage of directives.

``Aff``
-------

.. autoclass:: Aff

``Prefix`` and ``Suffix``
-------------------------

.. autoclass:: Affix
    :members:
.. autoclass:: Prefix
.. autoclass:: Suffix

Helper pattern-alike classes
----------------------------

This classes are wrapping several types of somewhat pattern-alike objects that can be ``*.aff``-file,
"compiling" them into something applyable much like Python's ``re`` module compiles regexps.

.. autoclass:: BreakPattern
.. autoclass:: Ignore
.. autoclass:: RepPattern
.. autoclass:: ConvTable
.. autoclass:: CompoundPattern
.. autoclass:: CompoundRule
.. autoclass:: PhonetTable
"""

import re
import functools
import itertools
from operator import itemgetter

from collections import defaultdict

from dataclasses import dataclass, field
from typing import List, Set, Dict, Tuple, Optional

from spylls.hunspell.algo.capitalization import Casing, GermanCasing, TurkicCasing
from spylls.hunspell.algo.trie import Trie


@dataclass
class BreakPattern:
    """
    Contents of the :attr:`Aff.BREAK` directive, pattern for splitting the word, compiled to regexp.

    Directives are stored this way:

    .. code-block:: text

        BREAK 3
        BREAK -
        BREAK ^-
        BREAK -$

    (That's, by the way, the default value of ``BREAK``). It means Hunspell while checking the word
    like "left-right", will check "left" and "right" separately; also will ignore "-" at the beginning
    and end of the word (second and third lines). Note that ``BREAK -`` without any special chars
    will NOT ignore "-" at the beginning/end.
    """
    pattern: str

    def __post_init__(self):
        # special chars like #, -, * etc should be escaped, but ^ and $ should be treated as in regexps
        pattern = re.escape(self.pattern).replace('\\^', '^').replace('\\$', '$')
        if pattern.startswith('^') or pattern.endswith('$'):
            self.regexp = re.compile(f"({pattern})")
        else:
            self.regexp = re.compile(f".({pattern}).")


@dataclass
class Ignore:
    """
    Contents of the :attr:`Aff.IGNORE` directive, chars to ignore on lookup/suggest, compiled with
    ``str.maketrans``.
    """
    chars: str

    def __post_init__(self):
        self.tr = str.maketrans('', '', self.chars)


@dataclass
class RepPattern:
    """
    Contents of the :attr:`Aff.REP` directive, pair of ``(frequent typo, its replacement)``. Typo pattern
    compiled to regexp.

    Example from Hunspell's docs, showing all the features:

    .. code-block:: text

        REP 5
        REP f ph
        REP ph f
        REP tion$ shun
        REP ^cooccurr co-occurr
        REP ^alot$ a_lot

    This means:

    * table of 5 replacements (first line):
    * try to see if "f -> ph" produces good word,
    * try "ph -> f",
    * at the end of the word try "tion -> shun",
    * at the beginning of the word try "cooccurr -> co-occurr",
    * and try to replace the whole word "alot" with "a lot" (``_`` stands for space).
    """
    pattern: str
    replacement: str

    def __post_init__(self):
        self.regexp = re.compile(self.pattern)


@dataclass
class Affix:
    """
    Common base for :class:`Prefix` and :class:`Suffix`.

    Affixes are stored in table looking this way:

    .. code-block:: text

        SFX X Y 1
        SFX X   0 able/CD . ds:able

    Meaning of the first line (table header):

    * Suffix (can be ``PFX`` for prefix)
    * ...designated by flag ``X``
    * ...supports cross-product (Y or N, "cross-product" means form with this suffix also allowed to
      have prefixes)
    * ...and there is 1 of them below

    Meaning of the table row:

    * Suffix X (should be same as table header)
    * ...when applies, doesn't change the stem (0 = "", but it can be "...removes some part at the end of the stem")
    * ...when applies, adds "able" to the stem
    * ...and the whole form will have also flags "C", "D"
    * ...condition of appplication is "any stem" (``.`` -- read it as regexp's "any char")
    * ...and the whole form would have data tags (morphology) ``ds:able``

    Then, if in the dictionary we have ``drink/X`` (can have the suffix marked by ``X``), the whole
    thing means "'drinkable' is a valid word form, has additional flags 'C', 'D' and some morphological info".

    Another example (from ``en_US.aff``):

    .. code-block:: text

        SFX N Y 3
        SFX N   e     ion        e
        SFX N   y     ication    y
        SFX N   0     en         [^ey]

    This defines suffix designated by flag ``N``, non-cross-productable, with 3 forms:

    * removes "e" and adds "ion" for words ending with "e" (animate => animation)
    * removes "y" and adds "icaton" for words ending with "y" (amplify => amplification)
    * removes nothing and adds "en" for words ending with neither (befall => befallen)

    *(TBH, I don't have a slightest idea why the third option is grouped with two previous... Probably
    because dictionary building is semi-automated process of "packing" word lists in dic+aff, and
    the "affixes" actually doesn't need to bear any grammatical sense.)*
    """

    #: Flag this affix marked with. Note that several affixes can have same flag (and in this case,
    #: which of them is relevant for the word, is decided by its :attr:`condition`)
    flag: str
    #: Whether this affix is compatible with opposite affix (e.g. if the word has both suffix and prefix,
    #: both of them should have ``crossproduct=True``)
    crossproduct: bool
    #: What is stripped from the stem when the affix is applied
    strip: str
    #: What is added when the affix is applied
    add: str
    #: Condition against which stem should be checked to understand whether this affix is relevant
    condition: str
    #: Flags this affix has
    flags: Set[str] = field(default_factory=set)


@dataclass
class Prefix(Affix):
    """
    :class:`Affix` at the beginning of the word, stored in :attr:`Aff.PFX` directive.
    """

    def __post_init__(self):
        # "-" does NOT have a special regex-meaning, while might happen as a regular word char (for ex., hu_HU)
        condition = self.condition.replace('-', '\\-')
        self.cond_regexp = re.compile('^' + condition)

        cond_parts = re.findall(r'(\[.+\]|[^\[])', condition)
        cond_parts = cond_parts[len(self.strip):]

        if cond_parts and cond_parts != ['.']:
            cond = '(?=' + ''.join(cond_parts) + ')'
        else:
            cond = ''

        self.lookup_regexp = re.compile('^' + self.add + cond)
        self.replace_regexp = re.compile('^' + self.add)

    def __repr__(self):
        return (
            f"Prefix({self.add}: {self.flag}{'×' if self.crossproduct else ''}" +
            (f"/{','.join(self.flags)}" if self.flags else '') +
            f", on ^{self.strip}[{self.condition}])"
        )


@dataclass
class Suffix(Affix):
    """
    :class:`Affix` at the end of the word, stored in :attr:`Aff.SFX` directive.
    """

    def __post_init__(self):
        # "-" does NOT have a special regex-meaning, while might happen as a regular word char (for ex., hu_HU)
        condition = self.condition.replace('-', '\\-')
        self.cond_regexp = re.compile(condition + '$')

        cond_parts = re.findall(r'(\[.+\]|[^\[])', condition)
        if self.strip:
            cond_parts = cond_parts[:-len(self.strip)]

        if cond_parts and cond_parts != ['.']:
            cond = '(' + ''.join(cond_parts) + ')'
        else:
            cond = ''

        self.lookup_regexp = re.compile(cond + self.add + '$')
        self.replace_regexp = re.compile(self.add + '$')

    def __repr__(self):
        return (
            f"Suffix({self.add}: {self.flag}{'×' if self.crossproduct else ''}" +
            (f"/{','.join(self.flags)}" if self.flags else '') +
            f", on [{self.condition}]{self.strip}$)"
        )


@dataclass
class CompoundRule:
    """
    Regexp-alike rule for generating compound words, content of :attr:`Aff.COMPOUNDRULE` directive.
    It is a way of specifying compounding alternative (and unrelated) to :attr:`Aff.COMPOUNDFLAG` and
    similar. Rules look this way:

    .. code-block:: text

        COMPOUNDRULE A*B?CD

    ...reading: compound word might consist of any number of words with flag ``A``, then 0 or 1 words
    with flag ``B``, then words with flags ``C`` and ``D``.

    ``en_US.aff`` uses this feature to specify spelling of numerals. In .aff-file, it has

    .. code-block:: text

        COMPOUNDRULE 2
        COMPOUNDRULE n*1t
        COMPOUNDRULE n*mp

    And, in .dic-file:

    .. code-block:: text

        0/nm
        0th/pt
        1/n1
        1st/p
        1th/tc
        2/nm
        2nd/p
        2th/tc
        # ...and so on...

    Which makes "111th" valid (one hundred eleventh): "1" with "n", "1" with "1" and "1th" with "t"
    is valid by rule ``n*1t``, but "121th" is not valid (should be "121st")
    """

    text: str

    def __post_init__(self):
        # TODO: proper flag parsing! Long is (aa)(bb)*(cc), numeric is (1001)(1002)*(1003)
        # This works but is super ad-hoc!
        if '(' in self.text:
            self.flags = set(re.findall(r'\((.+?)\)', self.text))
            parts = re.findall(r'\([^*?]+?\)[*?]?', self.text)
        else:
            self.flags = set(re.sub(r'[\*\?]', '', self.text))
            # There are ) flags used in real-life sv_* dictionaries
            # Obviously it is quite ad-hoc (other chars that have special meaning in regexp might be
            # used eventually)
            parts = [part.replace(')', '\\)') for part in re.findall(r'[^*?][*?]?', self.text)]

        self.re = re.compile(''.join(parts))
        self.partial_re = re.compile(
            functools.reduce(lambda res, part: f"{part}({res})?", parts[::-1])
        )

    def fullmatch(self, flag_sets):
        relevant_flags = [self.flags.intersection(f) for f in flag_sets]
        return any(
            self.re.fullmatch(''.join(fc))
            for fc in itertools.product(*relevant_flags)
        )

    def partial_match(self, flag_sets):
        relevant_flags = [self.flags.intersection(f) for f in flag_sets]
        return any(
            self.partial_re.fullmatch(''.join(fc))
            for fc in itertools.product(*relevant_flags)
        )


@dataclass
class CompoundPattern:
    """
    Pattern to check whether compound word is correct, stored in :attr:`Aff.CHECKCOMPOUNDPATTERN` directive.
    Format of the pattern:

    .. code-block:: text

        endchars[/flag] beginchars[/flag] [replacement]

    The pattern matches (telling that this compound is not allowed) if some pair of the words inside
    compound matches conditions:

    * first word ends with ``endchars`` (and have ``flags`` from the first element, if they are specified)
    * second word starts with ``beginchars`` (and have ``flags`` from the second element, if they are
      specified)

    ``endchars`` can be 0, specifying "word has zero affixes".

    ``replacement`` complicates things, allowing to specify "...but this string at the border of the
    words, should be unpacked into this ``endchars`` and that ``beginchars``, but make the compound
    allowed"... It complicates algorithm significantly, and **no known dictionary** uses this feature,
    so ``replacement`` is just ignored by Spylls.
    """

    left: str
    right: str
    replacement: Optional[str] = None

    def __post_init__(self):
        self.left_stem, _, self.left_flag = self.left.partition('/')
        self.right_stem, _, self.right_flag = self.right.partition('/')

        if self.left_stem == '0':
            self.left_stem = ''
            self.left_no_affix = True
        else:
            self.left_no_affix = False

        # FIXME: Hunpell docs say 0 is only allowed for the first pattern
        if self.right_stem == '0':
            self.right_stem = ''
            self.right_no_affix = True
        else:
            self.right_no_affix = False

    def match(self, left, right):
        return (left.stem.endswith(self.left_stem)) and (right.stem.startswith(self.right_stem)) and \
               (not self.left_no_affix or not left.is_base()) and \
               (not self.right_no_affix or not right.is_base()) and \
               (not self.left_flag or self.left_flag in left.flags()) and \
               (not self.right_flag or self.right_flag in right.flags())


@dataclass
class ConvTable:
    """
    Table of conversions that should be applied on pre- or post-processing, stored in :attr:`Aff.ICONV` and
    :attr:`Aff.OCONV`. Format is as follows (as far as I can guess from code and tests, documentation
    is very sparse):

    .. code-block:: text

        ICONV <number of entries>
        ICONV <pattern> <replacement>

    Typically, ``pattern`` and ``replacement`` are just simple strings, used mostly for replacing
    typographics (like trigraphs and "nice" apostrophes) before/after processing.

    But if there is a ``_`` in ``pattern``, it is treated as: regexp ``^`` if at the beginning of
    the pattern, regexp ``$`` if at the end, and just ignored otherwise. This seem to be a "hidden"
    feature, demonstrated by ``nepali.*`` set of tests in Hunspell distribution

    Conversion rules are applied as follows:

    * for each position in word
    * ...find any matching rules
    * ...chose the one with longest pattern
    * ...apply it, and shift to position after its applied (so there can't be recursive application
      of several rules on top of each other).
    """

    pairs: List[Tuple[str, str]]

    def __post_init__(self):
        def compile_row(pat1, pat2):
            pat1clean = pat1.replace('_', '')
            pat1re = pat1clean
            if pat1.startswith('_'):
                pat1re = '^' + pat1re
            if pat1.endswith('_'):
                pat1re = pat1re + '$'

            return (pat1clean, re.compile(pat1re), pat2.replace('_', ' '))

        # TODO: don't need key=?.. (default behavior)
        self.table = sorted([compile_row(*row) for row in self.pairs], key=itemgetter(0))

    def __call__(self, word):
        pos = 0
        res = ''
        while pos < len(word):
            matches = sorted(
                [(search, pattern, replacement)
                 for search, pattern, replacement in self.table
                 if pattern.match(word, pos)],
                key=lambda r: len(r[0]),
                reverse=True
            )
            if matches:
                search, pattern, replacement = matches[0]
                res += replacement
                pos += len(search)
            else:
                res += word[pos]
                pos += 1

        return res


@dataclass
class PhonetTable:
    """
    Represents table of metaphone transformations stored in :attr:`Aff.PHONE`. Format is borrowed
    from aspell and described `in its docs <http://aspell.net/man-html/Phonetic-Code.html>`_.

    Basically, each line of the table specifies pair of "pattern"/"replacement". Replacement is
    a literal string (with "_" meaning "empty string"), and pattern is ... complicated. Spylls, as
    of now, parses rules fully (see ``parse_rule`` method in the source), but doesn't implements all
    the algorithm's details (like rule prioritizing, concept of "follow-up rule" etc.)

    It is enough to pass Hunspell's (small) test for PHONE implementation, but definitely more naive
    than expected. But as it is marginal feature (and there are enough metaphone implementations in
    Python), we aren't (yet?) bothered by this fact.
    """
    table: List[Tuple[str, str]]

    RULE_PATTERN = re.compile(
        r'(?P<letters>\w+)(\((?P<optional>\w+)\))?(?P<lookahead>[-]+)?(?P<flags>[\^$<]*)(?P<priority>\d)?'
    )

    @dataclass
    class Rule:             # pylint: disable=missing-class-docstring
        search: re.Pattern
        replacement: str

        start: bool = False
        end: bool = False

        priority: int = 5

        followup: bool = True

        def match(self, word, pos):
            if self.start and pos > 0:
                return False
            if self.end:
                return self.search.fullmatch(word, pos)
            return self.search.match(word, pos)

    def __post_init__(self):
        self.rules = defaultdict(list)

        for search, replacement in self.table:
            self.rules[search[0]].append(self.parse_rule(search, replacement))

    def parse_rule(self, search: str, replacement: str) -> Rule:
        m = self.RULE_PATTERN.fullmatch(search)

        if not m:
            raise ValueError(f'Not a proper rule: {search!r}')

        text = [*m.group('letters')]
        if m.group('optional'):
            text.append('[' + m.group('optional') + ']')
        if m.group('lookahead'):
            la = len(m.group('lookahead'))
            regex = ''.join(text[:-la]) + '(?=' + ''.join(text[-la:]) + ')'
        else:
            regex = ''.join(text)

        return PhonetTable.Rule(
            search=re.compile(regex),
            replacement=replacement,
            start=('^' in m.group('flags')),
            end=('$' in m.group('flags')),
            followup=(m.group('lookahead') is not None)
        )


@dataclass
class Aff:
    """
    The class contains all directives from .aff file in its attributes.

    Attribute **names** are exactly the same as directives they've read from
    (they are upper-case, which is un-Pythonic, but allows to unambiguously relate directives to attrs and
    grep them in code).

    Attribute **values** are either appropriate primitive data types (strings, numbers, arrays etc),
    or simple objects wrapping this data to make it easily usable in algorithms (mostly it is some
    pattern-alike objects, like the result of Python's standard ``re.compile``, but specific for
    Hunspell domain).

    Attribute **docs** include explanations derived from
    `Hunspell's man page <https://www.manpagez.com/man/5/hunspell/>`_ (sometimes rephrased/abbreviated),
    plus links to relevant chunks of ``spylls`` code which uses the directive.

    Note that **all** directives are optional, empty .aff file is a valid one.

    **General**

    .. autoattribute:: SET
    .. autoattribute:: FLAG
    .. autoattribute:: LANG
    .. autoattribute:: WORDCHARS
    .. autoattribute:: IGNORE
    .. autoattribute:: CHECKSHARPS
    .. autoattribute:: FORBIDDENWORD

    **Suggestions**

    .. autoattribute:: KEY
    .. autoattribute:: TRY
    .. autoattribute:: NOSUGGEST
    .. autoattribute:: KEEPCASE
    .. autoattribute:: REP
    .. autoattribute:: MAP
    .. autoattribute:: NOSPLITSUGS
    .. autoattribute:: PHONE
    .. autoattribute:: MAXCPDSUGS

    **N-gram suggestions**

    .. autoattribute:: MAXNGRAMSUGS
    .. autoattribute:: MAXDIFF
    .. autoattribute:: ONLYMAXDIFF

    **Stemming**

    .. autoattribute:: PFX
    .. autoattribute:: SFX
    .. autoattribute:: NEEDAFFIX
    .. autoattribute:: CIRCUMFIX
    .. autoattribute:: COMPLEXPREFIXES
    .. autoattribute:: FULLSTRIP

    **Compounding**

    .. autoattribute:: BREAK
    .. autoattribute:: COMPOUNDRULE
    .. autoattribute:: COMPOUNDMIN
    .. autoattribute:: COMPOUNDWORDMAX
    .. autoattribute:: COMPOUNDFLAG
    .. autoattribute:: COMPOUNDBEGIN
    .. autoattribute:: COMPOUNDMIDDLE
    .. autoattribute:: COMPOUNDEND
    .. autoattribute:: ONLYINCOMPOUND
    .. autoattribute:: COMPOUNDPERMITFLAG
    .. autoattribute:: COMPOUNDFORBIDFLAG
    .. autoattribute:: FORCEUCASE
    .. autoattribute:: CHECKCOMPOUNDCASE
    .. autoattribute:: CHECKCOMPOUNDDUP
    .. autoattribute:: CHECKCOMPOUNDREP
    .. autoattribute:: CHECKCOMPOUNDTRIPLE
    .. autoattribute:: CHECKCOMPOUNDPATTERN
    .. autoattribute:: SIMPLIFIEDTRIPLE
    .. autoattribute:: COMPOUNDSYLLABLE
    .. autoattribute:: COMPOUNDMORESUFFIXES
    .. autoattribute:: COMPOUNDROOT

    **Pre/post-processing**

    .. autoattribute:: ICONV
    .. autoattribute:: OCONV

    **Aliasing**

    .. autoattribute:: AF
    .. autoattribute:: AM

    **Other/Ignored**

    .. autoattribute:: WARN
    .. autoattribute:: FORBIDWARN
    .. autoattribute:: SYLLABLENUM
    .. autoattribute:: SUBSTANDARD

    Some other directives that are in docs, but are deprecated/not used (and never implemented by Spylls):

    * ``LEMMA_PRESENT``

    **Derived attributes**

    This attributes are calculated after Aff reading and initialization

    .. py:attribute:: casing
        :type: spylls.hunspell.algo.capitalization.Casing

        "Casing" class (defining how the words in this language lowercased/uppercased). See
        :class:`Casing <spylls.hunspell.algo.capitalization.Casing>` for details. In ``Aff``, basically, it is

        * :class:`GermanCasing <spylls.hunspell.algo.capitalization.GermanCasing>` if :attr:`CHECKSHARPS`
          is ``True``,
        * :class:`TurkicCasing <spylls.hunspell.algo.capitalization.TurkicCasing>` if :attr:`LANG` is
          one of Turkic languages (Turkish, Azerbaijani, Crimean Tatar),
        * regular ``Casing`` otherwise.

    .. py:attribute:: suffixes_index
        :type: spylls.hunspell.algo.trie.Trie

        `Trie <https://en.wikipedia.org/wiki/Trie>`_ structure for fast selecting of all possible suffixes
        for some word, created from :attr:`SFX`

    .. py:attribute:: prefixes_index
        :type: spylls.hunspell.algo.trie.Trie

        `Trie <https://en.wikipedia.org/wiki/Trie>`_ structure for fast selecting all possible prefixes
        for some word, created from :attr:`PFX`
    """

    #: .aff and .dic encoding.
    #:
    #: *Usage*: Stored in :class:`readers.aff.Context <spylls.hunspell.readers.aff.Context>` and used
    #: for reopening .aff file (after the directive was read) in
    #: :meth:`reader_aff <spylls.hunspell.readers.aff.read_aff>`, and for opening .dic file
    #: in :meth:`reader_dic <spylls.hunspell.readers.dic.read_dic>`
    SET: str = 'Windows-1252'

    #: .aff file declares one of the possible flag formats:
    #:
    #: * ``short`` (default) -- each flag is one ASCII character
    #: * ``long`` -- each flag is two ASCII characters
    #: * ``numeric`` -- each flag is number, set of flags separates them with ``,``
    #: * ``UTF-8`` -- each flag is one UTF-8 character
    #:
    #: Flag format defines how flag sets attached to stems and affixes are parsed. For example,
    #: .dic file entry ``cat/ABCD`` can be considered having flags ``{"A", "B", "C", "D"}``
    #: (default flag format, "short"), or ``{"AB", "CD"}`` (flag format "long")
    #:
    #: *Usage*: Stored in :class:`readers.aff.Context <spylls.hunspell.readers.aff.Context>` and used
    #: in :meth:`reader_aff <spylls.hunspell.readers.aff.read_aff>`, and
    #: in :meth:`reader_dic <spylls.hunspell.readers.dic.read_dic>`
    FLAG: str = 'short'  # TODO: Enum of possible values, in fact

    #: ISO language code. The only codes that change behavior is codes of Turkic languages, which
    #: have different I/i capitalization logic.
    #:
    #: *Usage*: Abstracted into :attr:`casing` which is used in both lookup and suggest.
    LANG: Optional[str] = None

    #: Extends tokenizer of Hunspell command line interface with additional word characters, for example,
    #: dot, dash, n-dash, numbers.
    #:
    #: *Usage*: Not used in Spylls at all, as it doesn't do tokenization.
    WORDCHARS: Optional[str] = None

    #: Sets characters to ignore dictionary words, affixes and input words. Useful for optional characters,
    #: as Arabic (harakat) or Hebrew (niqqud) diacritical marks.
    #:
    #: *Usage*: in :meth:`Lookup.__call__ <spylls.hunspell.algo.lookup.Lookup.__call__>` for preparing
    #: input word, and in :meth:`reader_aff <spylls.hunspell.readers.aff.read_aff>`, and
    #: in :meth:`reader_dic <spylls.hunspell.readers.dic.read_dic>`.
    IGNORE: Optional[Ignore] = None

    #: Specify this language has German "sharp S" (ß), so this language is probably German
    #: :)
    #:
    #: This declaration effect is that uppercase word with "ß" letter is considered correct (uppercase
    #: form of "ß" is "SS", but it is allowed to leave downcased "ß"). The effect can be prohibited
    #: for some words by applying to word :attr:`KEEPCASE` flag (which for other situations has
    #: different meaning).
    #:
    #: *Usage:* To define whether to use
    #: :class:`GermanCasing <spylls.hunspell.algo.capitalization.GermanCasing>` in :attr:`casing`
    #: (which changes word lower/upper-casing slightly), and in
    #: :meth:`Lookup.good_forms <spylls.hunspell.algo.lookup.Lookup.good_forms>` to drop forms where
    #: lowercase "ß" is prohibited.
    CHECKSHARPS: bool = False

    #: Flag that marks word as forbidden. The main usage of this flag is to specify that some form
    #: that is logically possible (by affixing/suffixing or compounding) is in fact non-existent.
    #:
    #: Imaginary example (not from actual English dictionary!): let's say word "create" can have suffixes
    #: "-d", "-s", "-ion", and prefixes: "un-", "re-", "de-", but of all possible forms (created,
    #: creates, creation, uncreates, uncreation, ....) we decide "decreated" is not an existing word.
    #: Then we mark (in .dic file) word "create" with flag for all those suffixes and prefixes,
    #: but also add separate word "decreated" to dictionary, marked with flag that specified
    #: in .aff's FORBIDDENWORD directive. Now, this word wouldn't be considered correct, but all other
    #: combinations would.
    #:
    #: *Usage:* multiple times in both :class:`Lookup <spylls.hunspell.algo.lookup.Lookup>` and
    #: :class:`Suggest <spylls.hunspell.algo.suggest.Suggest>`
    FORBIDDENWORD: Optional[str] = None

    #: Flag to mark words which shouldn't be considered correct unless their casing is exactly like in
    #: the dictionary.
    #:
    #:      Note: With :attr:`CHECKSHARPS` declaration, words with sharp s (ß) and ``KEEPCASE`` flag
    #:      may be capitalized and uppercased, but uppercased forms of these words may not contain "ß",
    #:      only "SS".
    #:
    #: *Usage:* :meth:`Suggest.suggest_internal <spylls.hunspell.algo.suggest.Suggest.suggest_internal>`
    #: to produce suggestions in proper case,
    #: :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`.
    KEEPCASE: Optional[str] = None

    # **Suggestions**

    #: Flag to mark word/affix as "shouldn't be suggested" (but considered correct on lookup), like
    #: obscenities.
    #:
    #: *Usage:* on :class:`Suggest <spylls.hunspell.algo.suggest.Suggest>` creation (to make list of
    #: dictionary words for ngram-check), and in
    #: :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>` (if the lookup is
    #: called from suggest, with ``allow_nosuggest=False``)
    NOSUGGEST: Optional[str] = None

    #: String that specifies sets of adjacent characters on keyboard (so suggest could understand
    #: that "kitteb" is most probable misspelling of "kitten"). Format is "abc|def|xyz". For QWERTY
    #: English keyboard might be ``qwertyuiop|asdfghjkl|zxcvbnm``
    #:
    #: *Usage:*
    #: :meth:`Suggest.questionable_permutations <spylls.hunspell.algo.suggest.Suggest.questionable_permutations>`
    #: to pass to :meth:`permutations.badcharkey <spylls.hunspell.algo.permutations.badcharkey>`.
    KEY: str = ''

    #: List of all characters that can be used in words, *in order of probability* (most probable first),
    #: used on permutation for suggestions (trying to add missing, or replace erroneous character).
    #:
    #: *Usage:*
    #: :meth:`Suggest.questionable_permutations <spylls.hunspell.algo.suggest.Suggest.questionable_permutations>`
    #: to pass to :meth:`permutations.badchar <spylls.hunspell.algo.permutations.badchar>` and
    #: :meth:`permutations.forgotchar <spylls.hunspell.algo.permutations.forgotchar>`. Note that,
    #: obscurely enough, Suggest checks this option to
    #: decide whether dash should be used when suggesting two words (e.g. for misspelled "foobar",
    #: when it is decided that it is two words erroneously joined, suggest either returns only
    #: "foo bar", or also "foo-bar"). Whether dash is suggested, decided by presence of ``"-"`` in ``TRY``,
    #: or by presence of Latin ``"a"`` (= "the language use Latin script, all of them allow dashes
    #: between words")... That's how it is in Hunspell!
    TRY: str = ''

    #: *Table* of replacements for typical typos (like "shun"->"tion") to try on suggest. See :class:`RepPattern`
    #: for details of format.
    #:
    #: *Usage:* :meth:`Suggest.good_permutations <spylls.hunspell.algo.suggest.Suggest.good_permutations>` to pass to
    #: :meth:`permutations.replchars <spylls.hunspell.algo.permutations.replchars>`.
    #: Note that the table populated from aff's ``REP`` directive, *and* from dic's file ``ph:``
    #: tags (see :class:`Word <spylls.hunspell.data.dic.Word>` and
    #: :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>` for detailed explanations).
    REP: List[RepPattern] = field(default_factory=list)

    #: Sets of "similar" chars to try in suggestion (like ``aáã`` -- if they all exist in the language,
    #: replacing one in another would be a frequent typo). Several chars as a single entry should be
    #: grouped by parentheses: ``MAP ß(ss)`` (German "sharp s" and "ss" sequence are more or less the same).
    #:
    #: *Usage:*
    #: :meth:`Suggest.questionable_permutations <spylls.hunspell.algo.suggest.Suggest.questionable_permutations>`
    #: to pass to :meth:`permutations.mapchars <spylls.hunspell.algo.permutations.mapchars>`.
    MAP: List[Set[str]] = field(default_factory=list)

    #: Never try to suggest "this word should be split in two". LibreOffice sv_SE dictionary says
    #: "it is a must for Swedish". (Interestingly enough, Hunspell's tests doesn't check this flag at
    #: all).
    #:
    #: *Usage:*
    #: :meth:`Suggest.questionable_permutations <spylls.hunspell.algo.suggest.Suggest.questionable_permutations>`
    NOSPLITSUGS: bool = False

    #: Table for metaphone transformations. Format is borrowed from aspell and described
    #: `in its docs <http://aspell.net/man-html/Phonetic-Code.html>`_.
    #:
    #: Note that dictionaries with ``PHONE`` table are extremely rare: of all LibreOffice/Firefox
    #: dictionaries on en_ZA (South Africa) contains it -- though it is a generic English metaphone
    #: rules an it is quite weird they are not used more frequently.
    #:
    #: Showcase (with LibreOffice dictionaries)::
    #:
    #:  >>> misspelled = 'excersized'
    #:
    #:  >>> nometaphone = Dictionary.from_files('en/en_US')
    #:  >>> [*nometaphone.suggest(misspelled)])
    #:  ['supersized']
    #:
    #:  >>> withmetaphone = Dictionary.from_files('en/en_ZA')
    #:  >>> [*withmetaphone.suggest(misspelled)]
    #:  ['excerpted', 'exercised', 'excessive']
    #:
    #: *Usage:* :mod:`phonet_suggest <spylls.hunspell.algo.phonet_suggest>`
    PHONE: Optional[PhonetTable] = None

    #: Limits number of compound suggetions.
    #: Currently, not used in Spylls. See Suggest class comments about Hunspell/Spylls difference in
    #: handling separate "compound cycle".
    MAXCPDSUGS: int = 0

    # *NGram suggestions*:

    #: Set max. number of n-gram suggestions. Value 0 switches off the n-gram suggestions (see also
    #: :attr:`MAXDIFF`).
    #:
    #: *Usage:* :meth:`Suggest.ngram_suggestions <spylls.hunspell.algo.suggest.Suggest.ngram_suggestions>`
    #: (to decide whether ``ngram_suggest`` should be called at all) and
    #: :meth:`Suggest.suggest_internal <spylls.hunspell.algo.suggest.Suggest.suggest_internal>` (to limit
    #: amount of ngram-based suggestions).
    MAXNGRAMSUGS: int = 4

    #: Set the similarity factor for the n-gram based suggestions:
    #:
    #: * 5 = default value
    #: * 0 = fewer n-gram suggestions, but at least one;
    #: * 10 (max) = :attr:`MAXNGRAMSUGS` n-gram suggestions.
    #:
    #: *Usage:* :meth:`Suggest.ngram_suggestions <spylls.hunspell.algo.suggest.Suggest.ngram_suggestions>` where
    #: it is passed to :mod:`ngram_suggest <spylls.hunspell.algo.ngram_suggest>` module, and used in
    #: :meth:`detailed_affix_score <spylls.hunspell.algo.ngram_suggest.detailed_affix_score>`.
    MAXDIFF: int = -1

    #: Remove all bad n-gram suggestions (default mode keeps one, see :attr:`MAXDIFF`).
    #:
    #: *Usage:* :meth:`Suggest.ngram_suggestions <spylls.hunspell.algo.suggest.Suggest.ngram_suggestions>` where
    #: it is passed to :mod:`ngram_suggest <spylls.hunspell.algo.ngram_suggest>` module, and used in
    #: :meth:`filter_guesses <spylls.hunspell.algo.ngram_suggest.filter_guesses>`.
    ONLYMAXDIFF: bool = False

    # **Stemming**

    #: Dictionary of ``flag => prefixes with this flag``. See :class:`Affix` for detailed format and
    #: meaning description.
    #:
    #: Usage:
    #:
    #: * in :meth:`Suggest.ngram_suggestions <spylls.hunspell.algo.suggest.Suggest.ngram_suggestions>`
    #:   to pass to :mod:`ngram_suggest <spylls.hunspell.algo.ngram_suggest>`
    #:   (and there to construct all possible forms).
    #: * also parsed into :attr:`prefixes_index` Trie, which then used in
    #:   :meth:`Lookup.deprefix <spylls.hunspell.algo.lookup.Lookup.deprefix>`
    PFX: Dict[str, List[Prefix]] = field(default_factory=dict)

    #: Dictionary of ``flag => suffixes with this flag``. See :class:`Affix` for detailed format and
    #: meaning description.
    #:
    #: Usage:
    #:
    #: * in :meth:`Suggest.ngram_suggestions <spylls.hunspell.algo.suggest.Suggest.ngram_suggestions>`
    #:   to pass to :mod:`ngram_suggest <spylls.hunspell.algo.ngram_suggest>`
    #:   (and there to construct all possible forms).
    #: * also parsed into :attr:`suffixes_index` Trie, which then used in
    #:   :meth:`Lookup.desuffix <spylls.hunspell.algo.lookup.Lookup.desuffix>`
    SFX: Dict[str, List[Suffix]] = field(default_factory=dict)

    #: Flag saying "this stem can't be used without affixes". Can be also assigned to suffix/prefix,
    #: meaning "there should be other affixes besides this one".
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`
    NEEDAFFIX: Optional[str] = None

    #: Suffixes signed with this flag may be on a word when this word also has a prefix with
    #: this flag, and vice versa.
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`
    CIRCUMFIX: Optional[str] = None

    #: If two prefixes stripping is allowed (only one prefix by default). Random fun fact:
    #: of all currently available LibreOffice and Firefox dictionaries, only Firefox's Zulu has this
    #: flag.
    #:
    #: *Usage:* :meth:`Lookup.deprefix <spylls.hunspell.algo.lookup.Lookup.deprefix>`
    COMPLEXPREFIXES: bool = False

    #: If affixes are allowed to remove entire stem.
    #:
    #: Not used in Spylls (e.g. spylls doesn't fails when this option is False and entire word is removed,
    #: so hunspell's tests ``fullstrip.*`` are passing).
    FULLSTRIP: bool = False

    # **Compounding**

    #: Defines break points for breaking words and checking word parts separately. See :class:`BreakPattern`
    #: for format definition.
    #:
    #: *Usage:* :meth:`Lookup.break_word <spylls.hunspell.algo.lookup.Lookup.break_word>`
    BREAK: List[BreakPattern] = \
        field(default_factory=lambda: [BreakPattern('-'), BreakPattern('^-'), BreakPattern('-$')])

    #: Rule of producing compound words, with regexp-like syntax. See :class:`CompoundRule` for
    #: format definition.
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_rules <spylls.hunspell.algo.lookup.Lookup.compounds_by_rules>`
    COMPOUNDRULE: List[CompoundRule] = field(default_factory=list)

    #: Minimum length of words used for compounding.
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_rules <spylls.hunspell.algo.lookup.Lookup.compounds_by_rules>` &
    #: :meth:`Lookup.compounds_by_flags <spylls.hunspell.algo.lookup.Lookup.compounds_by_flags>`
    COMPOUNDMIN: int = 3

    #: Set maximum word count in a compound word.
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_rules <spylls.hunspell.algo.lookup.Lookup.compounds_by_rules>` &
    #: :meth:`Lookup.compounds_by_flags <spylls.hunspell.algo.lookup.Lookup.compounds_by_flags>`
    COMPOUNDWORDMAX: Optional[int] = None

    #: Forms with this flag (marking either stem, or one of affixes) can be part of the compound.
    #: Note that triple of flags :attr:`COMPOUNDBEGIN`, :attr:`COMPOUNDMIDDLE`, :attr:`COMPOUNDEND`
    #: is more precise way of marking ("this word can be at the beginning of compound").
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>` to compare
    #: form's compound position (or lack thereof) with presence of teh flag.
    COMPOUNDFLAG: Optional[str] = None

    #: Forms with this flag (marking either stem, or one of affixes) can be at the beginning of the
    #: compound.
    #: Part of the triple of flags :attr:`COMPOUNDBEGIN`, :attr:`COMPOUNDMIDDLE`, :attr:`COMPOUNDEND`;
    #: alternative to the triple is just :attr:`COMPOUNDFLAG` ("this form can be at any place in compound").
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`
    #: to compare form's compound position (or lack thereof) with the presence of the flag.
    COMPOUNDBEGIN: Optional[str] = None

    #: Forms with this flag (marking either stem, or one of affixes) can be in the middle of the
    #: compound (not the last part, and not the first).
    #: Part of the triple of flags :attr:`COMPOUNDBEGIN`, :attr:`COMPOUNDMIDDLE`, :attr:`COMPOUNDEND`;
    #: alternative to the triple is just :attr:`COMPOUNDFLAG` ("this form can be at any place in compound").
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`
    #: to compare form's compound position (or lack thereof) with the presence of the flag.
    COMPOUNDMIDDLE: Optional[str] = None

    #: Forms with this flag (marking either stem, or one of affixes) can be at the end of the
    #: compound.
    #: Part of the triple of flags :attr:`COMPOUNDBEGIN`, :attr:`COMPOUNDMIDDLE`, :attr:`COMPOUNDEND`;
    #: alternative to the triple is just :attr:`COMPOUNDFLAG` ("this form can be at any place in compound").
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`
    #: to compare form's compound position (or lack thereof) with the presence of the flag.
    COMPOUNDEND: Optional[str] = None

    #: Forms with this flag (marking either stem, or one of affixes) can only be part of the compound
    #: word, and never standalone.
    #:
    #: *Usage:* :meth:`Lookup.is_good_form <spylls.hunspell.algo.lookup.Lookup.is_good_form>`
    #: to compare form's compound position (or lack thereof) with the presence of the flag.
    #: Also in :class:`Suggest  <spylls.hunspell.algo.suggest.Suggest>` to produce list of the words
    #: suitable for ngram search.
    ONLYINCOMPOUND: Optional[str] = None

    #: Prefixes are allowed at the beginning of compounds, suffixes are allowed at the end of compounds
    #: by default. Affixes with ``COMPOUNDPERMITFLAG`` may be inside of compounds.
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_flags <spylls.hunspell.algo.lookup.Lookup.compounds_by_flags>`
    #: to make list of flags passed to
    #: :meth:`Lookup.produce_affix_forms <spylls.hunspell.algo.lookup.Lookup.produce_affix_forms>`
    #: (for this part of the compound, try find affixed spellings, you can use affixes with this flag).
    COMPOUNDPERMITFLAG: Optional[str] = None

    #: Prefixes are allowed at the beginning of compounds, suffixes are allowed at the end of compounds
    #: by default. Suffixes with ``COMPOUNDFORBIDFLAG`` may not be even at the end, and prefixes with
    #: this flag may not be even at the beginning.
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_flags <spylls.hunspell.algo.lookup.Lookup.compounds_by_flags>`
    #: to make list of flags passed to
    #: :meth:`Lookup.produce_affix_forms <spylls.hunspell.algo.lookup.Lookup.produce_affix_forms>`
    #: (for this part of the compound, try find affixed spellings, you can use affixes with this flag).
    COMPOUNDFORBIDFLAG: Optional[str] = None

    #: Last word part of a compound with flag FORCEUCASE forces capitalization of the whole compound
    #: word. Eg. Dutch word "straat" (street) with FORCEUCASE flags will allowed only in capitalized
    #: compound forms, according to the Dutch spelling rules for proper names.
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound <spylls.hunspell.algo.lookup.Lookup.is_bad_compound>`
    #: and
    #: :meth:`Suggest.suggest_internal <spylls.hunspell.algo.suggest.Suggest.suggest_internal>` (if
    #: this flag is present in the .aff file, we check that maybe
    #: just capitalization of misspelled word would make it right).
    FORCEUCASE: Optional[str] = None

    #: Forbid upper case characters at word boundaries in compounds.
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound <spylls.hunspell.algo.lookup.Lookup.is_bad_compound>`
    CHECKCOMPOUNDCASE: bool = False

    #: Forbid word duplication in compounds (e.g. "foofoo").
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound <spylls.hunspell.algo.lookup.Lookup.is_bad_compound>`
    CHECKCOMPOUNDDUP: bool = False

    #: Forbid compounding, if the (usually bad) compound word may be a non-compound word if some
    #: replacement by :attr:`REP` table (frequent misspellings) is made. Useful for languages with
    #: "compound friendly" orthography.
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound <spylls.hunspell.algo.lookup.Lookup.is_bad_compound>`
    CHECKCOMPOUNDREP: bool = False

    #: Forbid compounding, if compound word contains triple repeating letters (e.g. `foo|ox` or `xo|oof`).
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound <spylls.hunspell.algo.lookup.Lookup.is_bad_compound>`
    CHECKCOMPOUNDTRIPLE: bool = False

    #: List of patterns which forbid compound words when pair of words in compound matches this
    #: pattern. See :class:`CompoundPattern` for explanation about format.
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound <spylls.hunspell.algo.lookup.Lookup.is_bad_compound>`
    CHECKCOMPOUNDPATTERN: List[CompoundPattern] = field(default_factory=list)

    #: Allow simplified 2-letter forms of the compounds forbidden by :attr:`CHECKCOMPOUNDTRIPLE`.
    #: Example: "Schiff"+"fahrt" -> "Schiffahrt"
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_flags <spylls.hunspell.algo.lookup.Lookup.compounds_by_flags>`,
    #: after the main splitting cycle, we also try the
    #: hypothesis that if the letter on the current boundary is duplicated, we should triplicate it.
    SIMPLIFIEDTRIPLE: bool = False

    #: Need for special compounding rules in Hungarian.
    #:
    #: Not implemented in Spylls
    COMPOUNDSYLLABLE: Optional[Tuple[int, str]] = None

    #: Allow twofold suffixes within compounds.
    #:
    #: Not used in Spylls and doesn't have tests in Hunspell
    COMPOUNDMORESUFFIXES: bool = False

    # *Hu-only, COMPLICATED!*

    #: Need for special compounding rules in Hungarian. (The previous phrase is the only docs Hunspell provides ``:)``)
    #:
    #: Not used in Spylls.
    SYLLABLENUM: Optional[str] = None

    #: Flag that signs the compounds in the dictionary (Now it is used only in the Hungarian language specific code).
    #:
    #: Not used in Spylls.
    COMPOUNDROOT: Optional[str] = None

    # **Pre/post-processing**

    #: Input conversion table (what to do with word before checking if it is valid). See :class:`ConvTable`
    #: for format description.
    #:
    #: *Usage:* :meth:`Lookup.__call__ <spylls.hunspell.algo.lookup.Lookup.__call__>`
    ICONV: Optional[ConvTable] = None

    #: Output conversion table (what to do with suggestion before returning it to the user). See :class:`ConvTable`
    #: for format description.
    #:
    #: *Usage:* :meth:`Suggest.suggest_internal <spylls.hunspell.algo.suggest.Suggest.suggest_internal>`
    OCONV: Optional[ConvTable] = None

    # **Aliasing**

    #: Table of flag set aliases. Defined in .aff-file this way:
    #:
    #: .. code-block:: text
    #:
    #:    AF 3
    #:    AF ABC
    #:    AF BCD
    #:    AF DE
    #:
    #: This means set of flags "ABC" has an alias "1", "BCD" alias "2", "DE" alias "3" (aliases are
    #: just a sequental number in the table). Now, in .dic-file, ``foo/1`` would be equivalent of
    #: ``foo/ABC``, meaning stem ``foo`` has flags ``A, B, C``.
    #:
    #: *Usage:* Stored in :class:`readers.aff.Context <spylls.hunspell.readers.aff.Context>` to decode
    #: flags on reading .aff and .dic files.
    AF: Dict[str, Set[str]] = field(default_factory=dict)

    #: Table of word data aliases. Logic of aiasing is the same as for :attr:`AM`.
    #:
    #: *Usage:* :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>`
    AM: Dict[str, Set[str]] = field(default_factory=dict)

    # **Other**

    #: This flag is for rare words, which are also often spelling mistakes.
    #: With command-line flag ``-r``, Hunspell will warn about words with this flag in input text.
    #:
    #: Not implemented in Spylls
    WARN: Optional[str] = None

    #: Sets if words with :attr:`WARN` flag should be considered as misspellings (errors, not warnings).
    #:
    #: Not used in any known dictionary, and not implemented in Spylls (even in aff-reader).
    FORBIDWARN: bool = False

    #: Flag signs affix rules and dictionary words (allomorphs) not used in morphological generation
    #: and root words removed from suggestion.
    #:
    #: Not implemented in Spylls
    SUBSTANDARD: Optional[str] = None

    def __post_init__(self):
        suffixes = defaultdict(list)
        for suf in itertools.chain.from_iterable(self.SFX.values()):
            suffixes[suf.add[::-1]].append(suf)

        self.suffixes_index = Trie(suffixes)

        prefixes = defaultdict(list)
        for pref in itertools.chain.from_iterable(self.PFX.values()):
            prefixes[pref.add].append(pref)

        self.prefixes_index = Trie(prefixes)

        if self.CHECKSHARPS:
            self.casing = GermanCasing()
        elif self.LANG in ['tr', 'tr_TR', 'az', 'crh']:     # TODO: more robust language code check!
            self.casing = TurkicCasing()
        else:
            self.casing = Casing()
