from dataclasses import dataclass
from enum import Enum, auto

class Pos(Enum):
    BEGIN = auto()
    MIDDLE = auto()
    END = auto()

@dataclass
class Part:
    word: str
    pos: Pos

# TODO: Things to consider:
# * lazy return (yield) variants
# * order of variants (same as in hunspell)
# * some other settings of compounding: duplicated/triplicated letters, number of syllables in
#   root (hungarian) and so forth.
class Compounder:
    def __init__(self, checker, min_length=1, max_words=None):
        self.min_length = min_length
        self.max_words = max_words
        self.checker = checker

    def __call__(self, word):
        return self._split(word)

    def _split(self, word, prev_words=[]):
        res = [] if not prev_words else [[Part(word, Pos.END)]]
        if len(word) < self.min_length * 2 or (self.max_words and len(prev_words) >= self.max_words):
            return res

        for point in range(self.min_length, len(word) - self.min_length + 1):
            beg = Part(word[0:point], Pos.BEGIN if not prev_words else Pos.MIDDLE)
            words = [*prev_words, beg]
            if not self.checker(words): continue
            for rest in self._split(word[point:], words):
                res.append([beg, *rest])
        return res


        # res = [] if begin else [[Part(word, Pos.END)]]
        # if len(word) < self.min_length * 2 or (max and max == 1):
        #     return res

        # max = max - 1 if max else None
        # for point in range(self.min_length, len(word) - self.min_length + 1):
        #     beg = Part(word[0:point], Pos.BEGIN if begin else Pos.MIDDLE)
        #     for rest in self._split(word[point:], begin=False, max=max):
        #         res.append([beg, *rest])
        # return res
