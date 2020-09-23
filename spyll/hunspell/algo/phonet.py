import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterator, Tuple, List
from operator import itemgetter

from spyll.hunspell import data
import spyll.hunspell.algo.string_metrics as sm
from spyll.hunspell.algo.util import ScoredArray
import spyll.hunspell.algo.ngram_suggest as ng

MAX_ROOTS = 100


@dataclass
class Rule:
    PATTERN = re.compile(
                r'(?P<letters>\w+)(\((?P<optional>\w+)\))?(?P<lookahead>[-]+)?(?P<flags>[\^$<]*)(?P<priority>\d)?'
            )

    search: re.Pattern
    replacement: str

    start: bool = False
    end: bool = False

    priority: int = 5

    followup: bool = True

    def match(self, word, pos):
        if self.start and pos > 0:
            return False
        if self.end:
            return self.search.fullmatch(word, pos)
        return self.search.match(word, pos)

    @staticmethod
    def parse(search, replacement):
        m = Rule.PATTERN.fullmatch(search)

        if not m:
            raise ValueError(f'Not a proper rule: {search!r}')
        text = [*m.group('letters')]
        if m.group('optional'):
            text.append('[' + m.group('optional') + ']')
        if m.group('lookahead'):
            la = len(m.group('lookahead'))
            regex = ''.join(text[:-la]) + '(?=' + ''.join(text[-la:]) + ')'
        else:
            regex = ''.join(text)

        return Rule(
            search=re.compile(regex),
            replacement=replacement,
            start=('^' in m.group('flags')),
            end=('$' in m.group('flags')),
            followup=(m.group('lookahead') is not None)
        )


# http://aspell.net/man-html/Phonetic-Code.html
class Table:
    def __init__(self, source: List[Tuple[str, str]]):
        self.rules = defaultdict(list)

        for search, replacement in source:
            self.rules[search[0]].append(Rule.parse(search, replacement))

    def convert(self, word):
        # for each position in word:
        # find rules that match (^ -- only once, $ -- fullmatch)
        # "-" -- make them lookahead

        pos = 0
        word = word.upper()
        res = ''
        while pos < len(word):
            match = None
            for rule in self.rules[word[pos]]:
                match = rule.match(word, pos)
                if match:
                    res += rule.replacement
                    pos += match.span()[1] - match.span()[0]
                    break
            if not match:
                pos += 1
        return res


def phonet_suggest(word: str, *, roots, table: Table) -> Iterator[str]:
    word = word.lower()
    word_ph = table.convert(word)

    scores = ScoredArray[data.dic.Word](MAX_ROOTS)

    # NB: This cycle is repeated from ngram_suggest when both are used.
    # But it is MUCH easier to understand and test this way.
    for dword in roots:
        if abs(len(dword.stem) - len(word)) > 4:
            continue
        # TODO: more exceptions

        nscore = ng.root_score(word, dword.stem)
        if dword.phonetic():
            for variant in dword.phonetic():
                nscore = max(nscore, ng.root_score(word, variant))

        if nscore > 2 and abs(len(word) - len(dword.stem)) <= 3:
            score = 2 * sm.ngram(3, word_ph, table.convert(dword.stem), longer_worse=True)
            scores.push(dword.stem, score)

    guesses = sorted(scores.result(), key=itemgetter(1), reverse=True)

    # TODO: Use aff.MAXPHONSUGS setting
    guesses2 = [(dword, score + detailed_score(word, dword.lower())) for (dword, score) in guesses]
    guesses2 = sorted(guesses2, key=itemgetter(1), reverse=True)
    for (sug, _) in guesses2:
        yield sug


def detailed_score(word1: str, word2: str) -> float:
    return 2 * sm.lcslen(word1, word2) - abs(len(word1) - len(word2)) + sm.leftcommonsubstring(word1, word2)
