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
    flag: str='short' # TODO: Enum, in fact
    af: List[Tuple[int, Set[str]]] = field(default_factory=list)

    # Suggestions
    key: List[str] = field(default_factory=list) # in reader: "short" array (split by pipe)
    try_: str=''
    nosuggest: Flag=''
    maxcpdsugs: int=0
    rep: List[Tuple[str, str]] = field(default_factory=list)
    map: List[str] = field(default_factory=list)

    # Stemming
    pfx: List[Prefix] = field(default_factory=list)
    sfx: List[Suffix] = field(default_factory=list)
    circumfix: Flag=''
    needaffix: Flag=''
    forbiddenword: Flag=''

    # TODO: Compounding, IO, morphology
