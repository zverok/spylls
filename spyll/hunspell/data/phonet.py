import re

from collections import defaultdict
from dataclasses import dataclass

from typing import Tuple, List

RULE_PATTERN = re.compile(
    r'(?P<letters>\w+)(\((?P<optional>\w+)\))?(?P<lookahead>[-]+)?(?P<flags>[\^$<]*)(?P<priority>\d)?'
)


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
        return self.search.match(word, pos)


@dataclass
class Table:
    table: List[Tuple[str, str]]

    def __post_init__(self):
        self.rules = defaultdict(list)

        for search, replacement in self.table:
            self.rules[search[0]].append(parse_rule(search, replacement))


def parse_rule(search: str, replacement: str) -> Rule:
    m = RULE_PATTERN.fullmatch(search)

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
