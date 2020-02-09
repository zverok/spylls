from dataclasses import dataclass
from typing import List, Set

@dataclass
class Word:
    stem: str
    flags: Set[str]
    # TODO: morphology

@dataclass
class Dic:
    words: List[Word]
