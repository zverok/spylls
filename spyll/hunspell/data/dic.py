from collections import defaultdict
from dataclasses import dataclass
from typing import List, Set, Dict

from spyll.hunspell.algo.capitalization import Type as CapType


@dataclass
class Word:
    stem: str
    flags: Set[str]
    data: Dict[str, List[str]]
    captype: CapType
    alt_spellings: List[str]

    def __repr__(self):
        return f"Word({self.stem} /{','.join(self.flags)})"


@dataclass
class Dic:
    words: List[Word]

    def __post_init__(self):
        self.index = defaultdict(list)
        self.lowercase_index = defaultdict(list)

    def homonyms(self, word, *, ignorecase=False):
        if ignorecase:
            return self.lowercase_index.get(word, [])
        return self.index.get(word, [])

    def has_flag(self, word, flag, *, for_all=False):
        homonyms = self.homonyms(word)
        if for_all:
            return homonyms and all(flag in homonym.flags for homonym in homonyms)
        return homonyms and any(flag in homonym.flags for homonym in homonyms)

    def append(self, word, *, lower):
        self.words.append(word)
        self.index[word.stem].append(word)
        for lword in lower:
            self.lowercase_index[lword].append(word)
