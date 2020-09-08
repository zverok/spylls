import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo import permutations as pmt
from spyll.hunspell.algo import ngram_suggest, suggest

# dic = Dictionary('dictionaries/en_US')
dic = Dictionary('/home/zverok/projects/1foreign/LibreOffice-dictionaries/en/en_ZA')

print(list(suggest.suggest_debug(dic, 'enterperuner')))
print(list(suggest.suggest_debug(dic, 'excersized')))

