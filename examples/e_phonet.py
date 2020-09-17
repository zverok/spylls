import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo import permutations as pmt
from spyll.hunspell.algo import ngram_suggest, suggest
from spyll.hunspell.algo.phonet import Rule, Table, phonet_suggest

# dic = Dictionary('tests/fixtures/hunspell-orig/phone')
dic = Dictionary('tests/fixtures/hunspell-orig/en_US')

bad_flags = {*filter(None, [dic.aff.FORBIDDENWORD, dic.aff.NOSUGGEST, dic.aff.ONLYINCOMPOUND])}

roots = (word for word in dic.dic.words if not bad_flags.intersection(word.flags))

tbl = Table(dic.aff.PHONE)

print(list(phonet_suggest('wich', roots=roots, table=tbl)))
