import re
import functools
import itertools

from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional, NewType


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


@dataclass
class Suffix(Affix):
    def __post_init__(self):
        self.cond_regexp = re.compile(self.condition + '$')


@dataclass
class Aff:
    # General
    SET: str = 'Windows-1252'
    FLAG: str = 'short'  # TODO: Enum of possible values, in fact
    AF: List[Tuple[int, Set[str]]] = field(default_factory=list)

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

    # Stemming
    PFX: List[Prefix] = field(default_factory=dict)
    SFX: List[Suffix] = field(default_factory=dict)
    CIRCUMFIX: Optional[Flag] = None
    NEEDAFFIX: Optional[Flag] = None
    PSEUDOROOT: Optional[Flag] = None
    FORBIDDENWORD: Optional[Flag] = None
    BREAK: List[str] = field(default_factory=lambda: ['-', '^-', '-$'])

    # Compounding
    COMPOUNDRULE: List[str] = field(default_factory=list)

    COMPOUNDMIN: int = 3
    COMPOUNDWORDSMAX: Optional[int] = None

    COMPOUNDFLAG: Optional[Flag] = None

    COMPOUNDBEGIN: Optional[Flag] = None
    COMPOUNDMIDDLE: Optional[Flag] = None
    COMPOUNDLAST: Optional[Flag] = None

    ONLYINCOMPOUND: Optional[Flag] = None

    COMPOUNDPERMITFLAG: Optional[Flag] = None
    COMPOUNDFORBIDFLAG: Optional[Flag] = None

    CHECKCOMPOUNDCASE: bool = False
    CHECKCOMPOUNDDUP: bool = False
    CHECKCOMPOUNDREP: bool = False
    CHECKCOMPOUNDTRIPLE: bool = False
    CHECKCOMPOUNDPATTERN: List[Tuple[str, str, Optional[str]]] = field(default_factory=list)

    # IO:
    ICONV: List[Tuple[str, str]] = field(default_factory=list)
    OCONV: List[Tuple[str, str]] = field(default_factory=list)

    # TODO: morphology

    def use_dash(self) -> bool:
        return '-' in self.try_ or 'a' in self.try_
