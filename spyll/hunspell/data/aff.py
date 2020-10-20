import re
import functools
import itertools
from operator import itemgetter

from dataclasses import dataclass, field
from typing import List, Set, Dict, Tuple, Optional, NewType


Flag = NewType('Flag', str)


@dataclass
class BreakPattern:
    pattern: str

    def __post_init__(self):
        # special chars like #, -, * etc should be escaped, but ^ and $ should be treated as in regexps
        pattern = re.escape(self.pattern).replace('\\^', '^').replace('\\$', '$')
        if pattern.startswith('^') or pattern.endswith('$'):
            self.regexp = re.compile(f"({pattern})")
        else:
            self.regexp = re.compile(f".({pattern}).")


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
        self.cond_regexp = re.compile('^' + self.condition)

        cond_parts = re.findall(r'(\[.+\]|[^\[])', self.condition)
        cond_parts = cond_parts[len(self.strip):]

        if cond_parts and cond_parts != ['.']:
            cond = '(?=' + ''.join(cond_parts) + ')'
        else:
            cond = ''
        self.lookup_regexp = re.compile('^' + self.add + cond)

    def __repr__(self):
        return f"Prefix({self.flag}{'[x]' if self.crossproduct else ''}: "\
               f"{self.strip}[{self.condition}] => {self.add} /{','.join(self.flags)})"


@dataclass
class Suffix(Affix):
    def __post_init__(self):
        self.cond_regexp = re.compile(self.condition + '$')

        cond_parts = re.findall(r'(\[.+\]|[^\[])', self.condition)
        if self.strip:
            cond_parts = cond_parts[:-len(self.strip)]

        if cond_parts and cond_parts != ['.']:
            # We can't use actual Regexp lookbehind feature, as it has limited functionality
            # (should have known string length)
            cond = '(?P<lookbehind>' + ''.join(cond_parts) + ')'
        else:
            cond = '(?P<lookbehind>)'

        # print(cond)
        self.lookup_regexp = re.compile(cond + self.add + '$')
        self.replace_regexp = re.compile(self.add + '$')

    def __repr__(self):
        return f"Suffix({self.flag}{'[x]' if self.crossproduct else ''}: "\
               f"[{self.condition}]{self.strip} => {self.add} /{','.join(self.flags)})"


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
        # print(parts)
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
class Aff:
    # General
    SET: str = 'Windows-1252'
    FLAG: str = 'short'  # TODO: Enum of possible values, in fact
    LANG: Optional[str] = None
    WORDCHARS: Optional[str] = None
    IGNORE: Optional[str] = None

    # Suggestions
    KEY: str = ''
    TRY: str = ''
    NOSUGGEST: Optional[Flag] = None
    KEEPCASE: Optional[Flag] = None
    MAXCPDSUGS: int = 0
    REP: List[Tuple[str, str]] = field(default_factory=list)
    MAP: List[Set[str]] = field(default_factory=list)
    MAXDIFF: int = -1
    ONLYMAXDIFF: bool = False
    MAXNGRAMSUGS: int = 4
    NOSPLITSUGS: bool = False
    PHONE: List[Tuple[str, str]] = field(default_factory=list)

    # Stemming
    AF: Dict[int, Set[Flag]] = field(default_factory=dict)
    PFX: Dict[str, List[Prefix]] = field(default_factory=dict)
    SFX: Dict[str, List[Suffix]] = field(default_factory=dict)
    CIRCUMFIX: Optional[Flag] = None
    NEEDAFFIX: Optional[Flag] = None
    PSEUDOROOT: Optional[Flag] = None
    FORBIDDENWORD: Optional[Flag] = None
    BREAK: List[BreakPattern] = \
        field(default_factory=lambda: [BreakPattern('-'), BreakPattern('^-'), BreakPattern('-$')])
    COMPLEXPREFIXES: bool = False
    FULLSTRIP: bool = False
    WARN: Optional[Flag] = None

    CHECKSHARPS: bool = False

    # Compounding
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
    CHECKCOMPOUNDPATTERN: List[CompoundPattern] = field(default_factory=list)

    SIMPLIFIEDTRIPLE: bool = False

    COMPOUNDSYLLABLE: Optional[Tuple[int, str]] = None

    # Undocumented in most of publicly-available renderings, but documented in hunspell's source
    COMPOUNDMORESUFFIXES: bool = False

    # Hu-only, COMPLICATED
    SYLLABLENUM: Optional[Flag] = None
    COMPOUNDROOT: Optional[Flag] = None

    # IO:
    ICONV: Optional[ConvTable] = None
    OCONV: Optional[ConvTable] = None

    # Morphology
    AM: Dict[int, Set[str]] = field(default_factory=dict)

    # Ignored
    SUBSTANDARD: Optional[Flag] = None

    def use_dash(self) -> bool:
        return '-' in self.TRY or 'a' in self.TRY
