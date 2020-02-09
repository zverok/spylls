import re

from spyll.hunspell.readers import FileReader, util
from spyll.hunspell.data import dic

class DicReader:
    def __init__(self, path_or_io, encoding='ASCII', flag_format='short'):
        self.source = FileReader(path_or_io, encoding=encoding)
        self.flag_format = flag_format

    def __call__(self):
        words = []
        for (num, ln) in self.source:
            if num == 1 and re.match(r'^\d+$', ln): continue # It is words number, just skip

            # TODO: morphology
            if '/' in ln:
                word, flags = ln.split('/')
            else:
                word, flags = ln, ''

            words.append(dic.Word(stem=word, flags=util.parse_flags(flags, self.flag_format)))

        return dic.Dic(words=words)
