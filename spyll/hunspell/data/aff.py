"""
The module represents data from Hunspell's ``*.aff`` file.

Main Aff content
----------------

.. autodata:: Flag

.. autoclass:: Aff

Affixes
-------

.. autoclass:: Prefix
.. autoclass:: Suffix

Helper classes
--------------

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
from typing import List, Set, Dict, Tuple, Optional, NewType

from spyll.hunspell.algo.capitalization import Collation, GermanCollation, TurkicCollation
from spyll.hunspell.algo.trie import Trie


Flag = NewType('Flag', str)
"""
Flag is a short (1 or 2 chars typically) string to mark stems and affixes. See :attr:`Aff.FLAG`
for concept explantion.
"""


@dataclass
class BreakPattern:
    """
    Contents of the ``BREAK`` directive, pattern for splitting the word, compiled to regexp.
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
    Contents of the ``IGNORE`` directive, chars to ignore on lookup/suggest, compiled with
    ``str.maketrans``.
    """
    chars: str

    def __post_init__(self):
        self.tr = str.maketrans('', '', self.chars)


@dataclass
class RepPattern:
    """
    Contents of the ``REP`` directive, pair of ``(frequent typo, its replacement)``. Typo pattern
    compiled to regexp.
    """
    pattern: str
    replacement: str

    def __post_init__(self):
        self.regexp = re.compile(self.pattern)


@dataclass
class Affix:
    flag: Flag
    crossproduct: bool
    strip: str
    add: str
    condition: str
    flags: Set[Flag] = field(default_factory=set)


@dataclass
class Prefix(Affix):
    def __post_init__(self):
        # "-" does NOT have a special meaning, while might happen as a regular word char (for ex., hu_HU)
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
    def __post_init__(self):
        # "-" does NOT have a special meaning, while might happen as a regular word char (for ex., hu_HU)
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
    Represents table of metaphone transformations
    """
    table: List[Tuple[str, str]]

    RULE_PATTERN = re.compile(
        r'(?P<letters>\w+)(\((?P<optional>\w+)\))?(?P<lookahead>[-]+)?(?P<flags>[\^$<]*)(?P<priority>\d)?'
    )

    @dataclass
    class Rule:
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
    Base meaning of all options are documented in Hunspell's man page, for example here:
    https://www.systutorials.com/docs/linux/man/4-hunspell/

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

    *N-gram suggestions*

    .. autoattribute:: MAXDIFF
    .. autoattribute:: ONLYMAXDIFF
    .. autoattribute:: MAXNGRAMSUGS

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
    .. autoattribute:: SYLLABLENUM
    .. autoattribute:: COMPOUNDROOT

    **Pre/post-processing**

    .. autoattribute:: ICONV
    .. autoattribute:: OCONV

    **Aliasing**

    .. autoattribute:: AF
    .. autoattribute:: AM

    **Other**

    .. autoattribute:: WARN

    **Ignored**

    .. autoattribute:: SUBSTANDARD
    """

    #: .aff and .dic encoding. Stored in readers.aff.Context and used for reopening aff file, and
    #: for opening dic file
    SET: str = 'Windows-1252'
    #: ``*.aff`` file declares one of the possible flag formats:
    #:
    #: * `short` (default) -- each flag is one ASCII character
    #: * `long` -- each flag is two ASCII characters
    #: * `numeric` -- each flag is number, set of flags separates them with ``,``
    #: * `UTF-8` -- each flag is one UTF-8 character
    #:
    #: Flag format defines how flag sets attached to stems and affixes are parsed. For example,
    #: ``*.dic`` file entry ``cat/ABCD`` can be considered having flags ``{"A", "B", "C", "D"}``
    #: (default flag format, "short"), or ``{"AB", "CD"}`` (flag format "long")
    FLAG: str = 'short'  # TODO: Enum of possible values, in fact
    #: ISO language code. The only codes that change behavior is codes of Turkic languages, which
    #: have different I/i capitalization logic.
    #: Abstracted into Collation in Aff.__post_init__
    LANG: Optional[str] = None
    #: List of chars that can be in word. Not used in Spyll at all; in Hunspell is used for tokenization
    #: of text into words.
    WORDCHARS: Optional[str] = None
    #: List of chars to ignore in input words (for ex., vowels in Hebrew or Arabic)
    #: Used in Lookup.__call__ for preparing input word, and in read_dic/read_aff.
    IGNORE: Optional[Ignore] = None
    #: For German only: avoid uppercase ß, and only use SS
    CHECKSHARPS: bool = False
    #: Flag that marks word as forbidden. Used multiple times in both Lookup and Suggest
    FORBIDDENWORD: Optional[Flag] = None

    # **Suggestions**

    #: String that specifies sets of adjacent characters on keyboard (so suggest could understand
    #: that "kitteb" is most probable misspelling of "kitten"). Format is "abc|def|xyz"
    #:
    #: *Usage:*  :meth:`suggest.Suggest.good_permutations` to pass to :meth:`permutations.keychars`.
    KEY: str = ''
    #: List of all
    #:
    #: *Usage:* :meth:`suggest.Suggest.good_permutations` to pass to :meth:`permutations.badchar` and
    #: :meth:`permutations.forgotchar`. Note that, obscurely enough, Suggest checks this option to
    #: decide whether dash should be used when suggesting two words (e.g. for misspelled "foobar",
    #: when it is decided that it is two words erroneously joined, suggest either returns only
    #: "foo bar", or also "foo-bar"). Whether dash is suggested, decided by presence of ``"-"`` in TRY,
    #: or by presence of Latin ``"a"`` (= "the language use Latin script, all of them allow dashes
    #: between words")... That's how it is in Hunspell!
    TRY: str = ''
    #: Flag to mark word/affix as "shouldn't be suggested".
    #:
    #: *Usage:* Suggest.__init__ (to make list of dictionary words for ngram-check), and in
    #: Lookup.is_good_form (if the lookup is called from suggest, with allow_nosuggest=False)
    NOSUGGEST: Optional[Flag] = None
    #: Marks
    #:
    #: *Usage:* :meth:`Suggest.suggest_internal`, :meth:`Lookup.is_good_form`
    KEEPCASE: Optional[Flag] = None
    #: Table of replacements for typical typos (like "shun"->"tion")
    #:
    #: *Usage:* :meth:`suggest.Suggest.good_permutations` to pass to :meth:`permutations.replchars`.
    #: Note that the table populated from aff's ``REP`` directive, *and* from dic's file ``ph:``
    #: tags (see :meth:`readers.dic.read_dic`).
    REP: List[RepPattern] = field(default_factory=list)
    #: Sets of "similar" chars to try in suggestion (like "aáã" -- if they all exist in the language,
    #: replacing one in another would be a frequent typo).
    #:
    #: *Usage:* :meth:`suggest.Suggest.questionable_permutations` to pass to :meth:`permutations.mapchars`.
    MAP: List[Set[str]] = field(default_factory=list)
    #: Never try to suggest "this word should be split in two". LibreOffice sv_SE dictionary says
    #: "it is a must for Swedish". (Interestingly enough, Hunspell's tests doesn't check this flag at
    #: all).
    #:
    #: *Usage:* :meth:`suggest.Suggest.questionable_permutations`
    NOSPLITSUGS: bool = False
    #: Table for metaphone transformations.
    #:
    #: *Usage:* :mod:`phonet_suggest`
    PHONE: Optional[PhonetTable] = None
    #: Limits number of compound suggetions.
    #: Currently, not used in Spyll. See Suggest class comments about Hunspell/Spyll difference in
    #: handling separate "compound cycle".
    MAXCPDSUGS: int = 0

    # *NGram suggestions:
    MAXDIFF: int = -1
    ONLYMAXDIFF: bool = False
    MAXNGRAMSUGS: int = 4

    # **Stemming**

    #: Dictionary of ``flag => prefixes with this flag``
    #: *Usage:* in suggest.Suggest.ngram_suggest to pass to ngram_suggest (and there to construct
    #: all possible forms). In :meth:`Aff.__post_init__` there is also prefixes_index Trie constructed from
    #: PFX data, which then used in :meth:`Lookup.deprefix <spyll.hunspell.algo.lookup.Lookup.deprefix>`
    PFX: Dict[str, List[Prefix]] = field(default_factory=dict)
    #: Same as above, for suffixes
    #: *Usage:* suggest.Suggest.ngram_suggest, and lookup.Lookup.desuffix (derivative Trie)
    SFX: Dict[str, List[Suffix]] = field(default_factory=dict)
    #: Flag saying "this stem can't be used without affixes". Can be also assigned to suffix/prefix,
    #: meaning "there should be other affixes besides this one".
    #: *Usage:* lookup.Lookup.is_good_form
    NEEDAFFIX: Optional[Flag] = None
    #: Suffixes signed with CIRCUMFIX flag may be on a word when this word also has a prefix with
    #: CIRCUMFIX flag and vice versa.
    #: *Usage:* lookup.Lookup.is_good_form
    CIRCUMFIX: Optional[Flag] = None
    #: If two prefixes stripping is allowed (only one prefix by default). Random fun fact:
    #: of all currently available LibreOffice and Firefox dictionaries, only Firefox's Zulu has this
    #: flag
    #:
    #: *Usage:* lookup.Lookup.deprefix
    COMPLEXPREFIXES: bool = False
    FULLSTRIP: bool = False

    # **Compounding**

    #: List of patterns to break word
    #:
    #: *Usage:* :meth:`Lookup.try_break`
    BREAK: List[BreakPattern] = \
        field(default_factory=lambda: [BreakPattern('-'), BreakPattern('^-'), BreakPattern('-$')])

    #: List of rules
    #:
    #: *Usage:* :meth:`Lookup.compounds_by_rules`
    COMPOUNDRULE: List[CompoundRule] = field(default_factory=list)

    COMPOUNDMIN: int = 3
    COMPOUNDWORDMAX: Optional[int] = None

    COMPOUNDFLAG: Optional[Flag] = None

    COMPOUNDBEGIN: Optional[Flag] = None
    COMPOUNDMIDDLE: Optional[Flag] = None
    COMPOUNDEND: Optional[Flag] = None

    ONLYINCOMPOUND: Optional[Flag] = None

    COMPOUNDPERMITFLAG: Optional[Flag] = None
    COMPOUNDFORBIDFLAG: Optional[Flag] = None

    FORCEUCASE: Optional[Flag] = None

    CHECKCOMPOUNDCASE: bool = False
    CHECKCOMPOUNDDUP: bool = False
    CHECKCOMPOUNDREP: bool = False
    CHECKCOMPOUNDTRIPLE: bool = False
    #: List of patterns
    #:
    #: *Usage:* :meth:`Lookup.is_bad_compound`
    CHECKCOMPOUNDPATTERN: List[CompoundPattern] = field(default_factory=list)

    SIMPLIFIEDTRIPLE: bool = False

    COMPOUNDSYLLABLE: Optional[Tuple[int, str]] = None

    #: Undocumented in most of publicly-available renderings, but documented in hunspell's source
    COMPOUNDMORESUFFIXES: bool = False

    # Hu-only, COMPLICATED
    SYLLABLENUM: Optional[Flag] = None
    COMPOUNDROOT: Optional[Flag] = None

    # **Pre/post-processing**

    ICONV: Optional[ConvTable] = None
    OCONV: Optional[ConvTable] = None

    # **Aliasing**

    #: Numbered list of flag set aliases
    #:
    #: *Usage:* Put in :class:`readers.aff.Context` to decode flags on reading ``*.aff`` and ``*.dic``
    AF: Dict[str, Set[Flag]] = field(default_factory=dict)
    #: Numbered list of word data ("morphological info") aliases
    #:
    #: *Usage:* :meth:`readers.aff.read_dic`
    AM: Dict[str, Set[str]] = field(default_factory=dict)

    # **Other**

    WARN: Optional[Flag] = None
    # TODO: FORBIDWARN

    # Ignored
    SUBSTANDARD: Optional[Flag] = None

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
            self.collation = GermanCollation()
        elif self.LANG in ['tr', 'tr_TR', 'az', 'crh']:     # TODO: more robust language code check!
            self.collation = TurkicCollation()
        else:
            self.collation = Collation()
