import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo.lookup import analyze

dic = Dictionary('tests/fixtures/hunspell-orig/base_utf')

# print(dic.aff.pfx)
print(list(analyze(dic.aff, dic.dic, 'İZMİR')))
