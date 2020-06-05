import re

from spyll.hunspell.readers import FileReader
from spyll.hunspell.data import dic


def read_dic(path_or_io, *, flag_parser, encoding='ASCII'):
    source = FileReader(path_or_io, encoding=encoding)

    def read_word(line):
        parts = re.split(r"\s+", line)
        word_parts = [part for part in parts if not re.match(r'^(\w{2}:\S+|\d+)$', part)]

        word, _, flags = ' '.join(word_parts).partition('/')

        return dic.Word(stem=word, flags={*flag_parser.parse(flags)})

    words = [
        read_word(line)
        for num, line in source
        if not (num == 1 and re.match(r'^\d+$', line))
    ]

    return dic.Dic(words=words)
