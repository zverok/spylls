import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo import permutations as pmt

dic = Dictionary('tests/fixtures/hunspell-orig/base')

# print(list(pmt.permutations('rotten-day', use_dash=True)))
# print([sug for sug in pmt.twowords('rottenday', use_dash=True) if type(sug) == tuple])

# print(dic.roots())
print(list(dic.suggest('rottenday')))
