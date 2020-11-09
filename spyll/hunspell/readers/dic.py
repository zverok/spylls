from collections import defaultdict
import re

from spyll.hunspell.data import dic

SPACES_REGEXP = re.compile(r"\s+")
MORPH_REGEXP = re.compile(r'^(\w{2}:\S*|\d+)$')
SLASH_REGEXP = re.compile(r'(?<!\\)/')


def read_dic(source, *, context):
    def read_word(line):
        word_parts = []
        morphology = defaultdict(list)

        for i, part in enumerate(SPACES_REGEXP.split(line)):
            if ':' in part and i != 0:
                tag, _, content = part.partition(':')
                # TODO: in ph2.dic, there is "ph:" construct, what does it means?..
                if content:
                    morphology[tag].append(content)
            elif part.isdigit():
                pass    # TODO: AM
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

        return dic.Word(stem=word, flags={*context.parse_flags(flags)}, morphology=morphology)

    words = [
        read_word(line)
        for num, line in source
        if not (num == 1 and re.match(r'^\d+$', line))
    ]

    return dic.Dic(words=words)
