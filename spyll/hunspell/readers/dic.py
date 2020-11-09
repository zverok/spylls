from collections import defaultdict
import re

from spyll.hunspell.data import dic
from spyll.hunspell.data.aff import RepPattern

from spyll.hunspell.algo.capitalization import Type as CapType


COUNT_REGEXP = re.compile(r'^\d+(\s+|$)') # should start with digits, but can have whatever further
SPACES_REGEXP = re.compile(r"\s+")
MORPH_REGEXP = re.compile(r'^(\w{2}:\S*|\d+)$')
SLASH_REGEXP = re.compile(r'(?<!\\)/')


def read_dic(source, *, aff, context):
    result = dic.Dic(words=[])

    for num, line in source:
        if num == 1 and COUNT_REGEXP.match(line):
            continue

        word_parts = []
        data = defaultdict(list)

        parts = SPACES_REGEXP.split(line)

        for i, part in enumerate(parts):
            if ':' in part and i != 0:
                tag, _, content = part.partition(':')
                # TODO: in ph2.dic, there is "ph:" construct, what does it means?..
                if content:
                    data[tag].append(content)
            elif part.isdigit() and i != 0:
                parts.extend(aff.AM[part])
            else:
                word_parts.append(part)

        word = ' '.join(word_parts)
        if word.startswith('/'):
            flags = ''
        else:
            word_with_flags = SLASH_REGEXP.split(word, 2)
            if len(word_with_flags) == 2:
                word, flags = word_with_flags
            else:
                flags = ''
        if r'\/' in word:
            word = word.replace(r'\/', '/')
        if context.ignore:
            word = word.translate(context.ignore.tr)

        captype = aff.collation.guess(word)
        lower = aff.collation.lower(word) if captype != CapType.NO else word
        alt_spellings = []

        if 'ph' in data:
            for pattern in data['ph']:
                # TODO: https://manpages.debian.org/experimental/libhunspell-dev/hunspell.5.en.html#Optional_data_fields
                # according to it, Wednesday ph:wendsay should produce two cases
                #   REP wendsay Wednesday
                #   REP Wendsay Wednesday
                # hunspell handles it by just `if (captype==INITCAP)`...
                if pattern.endswith('*'):
                    aff.REP.append(RepPattern(pattern[:-2], word[:-1]))
                elif '->' in pattern:
                    fro, _, to = pattern.partition('->')
                    aff.REP.append(RepPattern(fro, to))
                else:
                    alt_spellings.append(pattern)
                    aff.REP.append(RepPattern(pattern, word))

        word_obj = dic.Word(
            stem=word,
            flags={*context.parse_flags(flags)},
            data=data,
            captype=captype,
            alt_spellings=alt_spellings
        )
        result.append(word_obj, lower=lower)

    return result
