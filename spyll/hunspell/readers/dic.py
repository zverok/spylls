import re

from spyll.hunspell.readers import FileReader
from spyll.hunspell.data import dic

def read_dic(path_or_io, *, flag_parser, encoding='ASCII'):
    source = FileReader(path_or_io, encoding=encoding)

    def read_word(line):
        word, _, morphology = line.partition("\t")

        word, _, flags = word.partition('/')

        return dic.Word(stem=word, flags={*flag_parser.parse(flags)})

    words = [
        read_word(line)
        for num, line in source
        if not (num == 1 and re.match(r'^\d+$', line))
    ]

    return dic.Dic(words=words)
