import re
import os.path

from spyll.hunspell.dictionary import Dictionary
# from spyll.hunspell.algo.lookup import analyze
from spyll.hunspell.algo.lookup import CompoundPos

dic = Dictionary.from_files('tests/integrational/fixtures/base')

# print(dic.dic.words[1].flags, dic.aff.FORCEUCASE)
# print(dic.dic.has_flag('bar', dic.aff.FORCEUCASE))
# print(*dic.lookuper.good_forms('foobazbar'))
# print(*dic.lookuper.good_forms('foobarbaz'))

# for k, vals in dic.aff.suffixes_index.index.items():
#     print(f"{k}: {vals}")

print(dic.lookup('FAQs'))
