import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo.lookup import analyze

dic = Dictionary('tests/fixtures/hunspell-orig/morph')

# print(dic.aff.pfx)
print(list(analyze(dic.aff, dic.dic, 'drinkables')))
