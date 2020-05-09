import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo import permutations as pmt

dic = Dictionary('tests/fixtures/hunspell-orig/map')

print(dic.aff.map)
print(list(pmt.mapchars('Fruhstuck', dic.aff.map)))

print(dic.roots())
print(list(dic.suggest('Fruhstuck')))
