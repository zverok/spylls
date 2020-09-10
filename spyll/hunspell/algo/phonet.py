import re
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Rule:
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
        else:
            return self.search.match(word, pos)

    def parse(search, replacement):
        m = re.fullmatch(r'(?P<letters>\w+)(\((?P<optional>\w+)\))?(?P<lookahead>[-]+)?(?P<flags>[\^$<]*)(?P<priority>\d)?', search)
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
class Phonet:
    def __init__(self, table: List[Tuple[str, str]]):
        self.rules = defaultdict(list)

        for search, replacement in table:
            self.rules[search[0]].append(Rule.parse(search, replacement))

    def convert(self, word):
        # for each position in word:
        # find rules that match (^ -- only once, $ -- fullmatch)
        # "-" -- make them lookahead

        pos = 0
        word = word.upper()
        res = ''
        while pos < len(word):
            for rule in self.rules[word[pos]]:
                match = rule.match(word, pos)
                if match:
                    res += rule.replacement
                    pos += match.span()[1] - match.span()[0]
                    break
            if not match:
                # res += word[pos]
                pos += 1
        return res
