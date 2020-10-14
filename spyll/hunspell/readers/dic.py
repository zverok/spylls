from collections import defaultdict
import re

from spyll.hunspell.data import dic

SPACES_REGEXP = re.compile(r"\s+")
MORPH_REGEXP = re.compile(r'^(\w{2}:\S*|\d+)$')


def read_dic(source, *, context):
    tr = str.maketrans('', '', context.ignore)

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

        word, _, flags = ' '.join(word_parts).partition('/')
        if context.ignore:
            word = word.translate(tr)

        return dic.Word(stem=word, flags={*context.parse_flags(flags)}, morphology=morph)

    words = [
        read_word(line)
        for num, line in source
        if not (num == 1 and re.match(r'^\d+$', line))
    ]

    return dic.Dic(words=words)
