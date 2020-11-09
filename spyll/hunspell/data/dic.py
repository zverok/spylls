import itertools
from dataclasses import dataclass
from typing import List, Set, Dict


@dataclass
class Word:
    stem: str
    flags: Set[str]
    morphology: Dict[str, str]

    def phonetic(self):
        return self.morphology.get('ph')

    def __repr__(self):
        return f"Word({self.stem} /{','.join(self.flags)})"


@dataclass
class Dic:
    words: List[Word]

    def __post_init__(self):
        # TODO: On dictionary creation
        self.index = {
            stem: list(words)
            for stem, words in itertools.groupby(self.words, lambda w: w.stem)
        }
        self.index_l = {
            # TODO: use collation!
            stem.lower(): list(words)
            for stem, words in itertools.groupby(self.words, lambda w: w.stem)
        }

    def homonyms(self, word, *, ignorecase=False):
        if ignorecase:
            return self.index_l.get(word, [])
        return self.index.get(word, [])

    def has_flag(self, word, flag, *, for_all=False):
        homonyms = self.homonyms(word)
        if for_all:
            return homonyms and all(flag in homonym.flags for homonym in homonyms)
        return homonyms and any(flag in homonym.flags for homonym in homonyms)

    # def push_word(stem, flags, data, alt_spellings):
    #     captype = collation.guess(word)
    #     word = Word(stem=stem, flags=flags, data=data, captype=captype)
    #     self.index[stem].append(word)
    #     lower = collation.lower(stem) if captype != CapType.NO else stem
    #     self.lowercase_index[stem].append(word)
    #     self.reptable.expand(alt_spellings)
