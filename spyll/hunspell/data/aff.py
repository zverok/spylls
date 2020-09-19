import re

from dataclasses import dataclass, field
from typing import List, Set, Dict, Tuple, Optional, NewType


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
        self.cond_regexp = re.compile('^' + self.condition)

    def __repr__(self):
        return f"Prefix({self.flag}{'[x]' if self.crossproduct else ''}: "\
               f"{self.strip}[{self.condition}] => {self.add} /{','.join(self.flags)})"


@dataclass
class Suffix(Affix):
    def __post_init__(self):
        self.cond_regexp = re.compile(self.condition + '$')

    def __repr__(self):
        return f"Suffix({self.flag}{'[x]' if self.crossproduct else ''}: "\
               f"[{self.condition}]{self.strip} => {self.add} /{','.join(self.flags)})"


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
    PFX: List[Prefix] = field(default_factory=dict)
    SFX: List[Suffix] = field(default_factory=dict)
    CIRCUMFIX: Optional[Flag] = None
    NEEDAFFIX: Optional[Flag] = None
    PSEUDOROOT: Optional[Flag] = None
    FORBIDDENWORD: Optional[Flag] = None
    BREAK: List[str] = field(default_factory=lambda: ['-', '^-', '-$'])
    COMPLEXPREFIXES: bool = False
    FULLSTRIP: bool = False
    WARN: Optional[Flag] = None

    CHECKSHARPS: bool = False

    # Compounding
    COMPOUNDRULE: List[str] = field(default_factory=list)

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
    CHECKCOMPOUNDPATTERN: List[Tuple[str, str, Optional[str]]] = field(default_factory=list)

    SIMPLIFIEDTRIPLE: bool = False

    COMPOUNDSYLLABLE: Optional[Tuple[int, str]] = None

    # IO:
    ICONV: List[Tuple[str, str]] = field(default_factory=list)
    OCONV: List[Tuple[str, str]] = field(default_factory=list)

    # Morphology
    AM: Dict[int, Set[str]] = field(default_factory=dict)

    def use_dash(self) -> bool:
        return '-' in self.TRY or 'a' in self.TRY
