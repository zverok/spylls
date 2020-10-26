from collections import defaultdict
import re

from spyll.hunspell.data import dic

SPACES_REGEXP = re.compile(r"\s+")
MORPH_REGEXP = re.compile(r'^(\w{2}:\S*|\d+)$')
SLASH_REGEXP = re.compile(r'(?<!\\)/')


def read_dic(source, *, context):
    def read_word(line):
        parts = SPACES_REGEXP.split(line)
        word_parts = [part for part in parts if not MORPH_REGEXP.match(part)]

        def morphology(parts):
            # Todo: AM
            for part in parts:
                tag, _, content = part.partition(':')
                if content:
                    yield tag, content

        morph = defaultdict(list)
        for tag, content in morphology(parts):
            morph[tag].append(content)

        word = ' '.join(word_parts)
        if word.startswith('/'):
            flags = ''
        else:
            word_with_flags = SLASH_REGEXP.split(word, 2)
            if len(word_with_flags) == 2:
                word, flags = word_with_flags
            else:
                flags = ''
        word = word.replace('\\/', '/')
        if context.ignore:
            word = word.translate(context.ignore.tr)

        return dic.Word(stem=word, flags={*context.parse_flags(flags)}, morphology=morph)

    words = [
        read_word(line)
        for num, line in source
        if not (num == 1 and re.match(r'^\d+$', line))
    ]

    return dic.Dic(words=words)
