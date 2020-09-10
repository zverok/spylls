import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo import permutations as pmt
from spyll.hunspell.algo import ngram_suggest, suggest
from spyll.hunspell.algo.phonet import Rule, Phonet

# dic = Dictionary('tests/fixtures/hunspell-orig/phone')
dic = Dictionary('tests/fixtures/hunspell-orig/en_US')

# print(dic.aff.PHONE)

r = Rule.parse('UH(AEIOUY)-^', '*H')
print(r)
r = Rule.parse('TT-', '')
print(r)

tbl = Phonet(dic.aff.PHONE)

print(tbl.convert('knight'))
print(tbl.convert('pig'))
print(tbl.convert('architect'))
print(tbl.convert('bajador'))
