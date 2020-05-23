import re
import functools
import itertools

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional, NewType

from pygtrie import CharTrie

Flag = NewType('Flag', str)


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
        cond_parts = re.findall(r'(\[.+\]|[^\[])', self.condition)
        if self.strip:
            cond_parts = cond_parts[len(self.strip):]

        if cond_parts and cond_parts != ['.']:
            cond = '(?=' + ''.join(cond_parts) + ')'
        else:
            cond = ''
        self.regexp = re.compile('^' + self.add + cond)
        self.cond_regexp = re.compile('^' + self.condition)


@dataclass
class Suffix(Affix):
    def __post_init__(self):
        cond_parts = re.findall(r'(\[.+\]|[^\[])', self.condition)
        if self.strip:
            cond_parts = cond_parts[:-len(self.strip)]

        if cond_parts and cond_parts != ['.']:
            cond = '(?<=' + ''.join(cond_parts) + ')'
        else:
            cond = ''
        self.regexp = re.compile(cond + self.add + '$')
        self.cond_regexp = re.compile(self.condition + '$')


@dataclass
class CompoundRule:
    text: str

    def __post_init__(self):
        # TODO: proper flag parsing! Long is (aa)(bb)*(cc), numeric is (1001)(1002)*(1003)
        self.flags = set(re.sub(r'[\*\?]', '', self.text))
        parts = re.findall(r'[^*?][*?]?', self.text)
        self.re = re.compile(self.text)
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
class Aff:
    # General
    set: str = 'Windows-1252'
    flag: str = 'short'  # TODO: Enum of possible values, in fact
    af: List[Tuple[int, Set[str]]] = field(default_factory=list)

    # Suggestions
    key: str = ''
    try_: str = ''  # actually just TRY, but conflicts with Python keyword
    nosuggest: Optional[Flag] = None
    keepcase: Optional[Flag] = None
    maxcpdsugs: int = 0
    rep: List[Tuple[str, str]] = field(default_factory=list)
    map: List[Set[str]] = field(default_factory=list)
    maxdiff: int = -1
    onlymaxdiff: bool = False
    maxngramsugs: int = 4

    # Stemming
    pfx: List[Prefix] = field(default_factory=dict)
    sfx: List[Suffix] = field(default_factory=dict)
    circumfix: Optional[Flag] = None
    needaffix: Optional[Flag] = None
    pseudoroot: Optional[Flag] = None
    forbiddenword: Optional[Flag] = None

    # Compounding
    compoundrule: List[str] = field(default_factory=list)
    compoundmin: int = 3
    compoundwordsmax: Optional[int] = None
    compoundflag: Optional[Flag] = None
    compoundbegin: Optional[Flag] = None
    compoundmiddle: Optional[Flag] = None
    compoundlast: Optional[Flag] = None
    onlyincompound: Optional[Flag] = None
    compoundpermitflag: Optional[Flag] = None
    compoundforbidflag: Optional[Flag] = None

    # IO:
    oconv: List[Tuple[str, str]] = field(default_factory=list)

    # TODO: IO, morphology

    def __post_init__(self):
        self.compoundrules = [CompoundRule(r) for r in self.compoundrule]

        self.suffixes = CharTrie()
        self.prefixes = CharTrie()

        for _, sufs in self.sfx.items():
            for suf in sufs:
                self.suffixes[suf.add[::-1]] = suf

        for _, prefs in self.pfx.items():
            for pref in prefs:
                self.prefixes[pref.add] = pref

    def use_dash(self) -> bool:
        return '-' in self.try_ or 'a' in self.try_
