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

class Prefix(Affix):
    pass

class Suffix(Affix):
    pass

@dataclass
class Aff:
    # General
    set: str='UTF-8'
    flag: str='short' # TODO: Enum of possible values, in fact
    af: List[Tuple[int, Set[str]]] = field(default_factory=list)

    # Suggestions
    key: List[str] = field(default_factory=list) # in reader: "short" array (split by pipe)
    try_: str=''
    nosuggest: Optional[Flag] = None
    maxcpdsugs: int=0
    rep: List[Tuple[str, str]] = field(default_factory=list)
    map: List[str] = field(default_factory=list)

    # Stemming
    pfx: List[Prefix] = field(default_factory=list)
    sfx: List[Suffix] = field(default_factory=list)
    circumfix: Optional[Flag] = None
    needaffix: Optional[Flag] = None
    pseudoroot: Optional[Flag] = None
    forbiddenword: Optional[Flag] = None

    # Compounding
    compoundrule: List[str] = field(default_factory=list)
    compoundmin: int=3
    compoundwordsmax: Optional[int]=None
    compoundflag: Optional[Flag] = None
    compoundbegin: Optional[Flag] = None
    compoundmiddle: Optional[Flag] = None
    compoundlast: Optional[Flag] = None
    onlyincompound: Optional[Flag] = None
    compoundpermitflag: Optional[Flag] = None
    compoundforbidflag: Optional[Flag] = None

    # TODO: IO, morphology
