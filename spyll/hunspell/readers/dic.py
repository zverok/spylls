from collections import defaultdict
import re

from spyll.hunspell.readers import FileReader
from spyll.hunspell.data import dic


def read_dic(path_or_io, *, context):
    source = FileReader(path_or_io, encoding=context.encoding)

    def read_word(line):
        parts = re.split(r"\s+", line)
        word_parts = [part for part in parts if not re.match(r'^(\w{2}:\S*|\d+)$', part)]

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
        word = word.translate(str.maketrans('', '', context.ignore))

        return dic.Word(stem=word, flags={*context.parse_flags(flags)}, morphology=morph)

    words = [
        read_word(line)
        for num, line in source
        if not (num == 1 and re.match(r'^\d+$', line))
    ]

    return dic.Dic(words=words)
