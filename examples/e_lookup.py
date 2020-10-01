import re
import os.path

from spyll.hunspell.dictionary import Dictionary
# from spyll.hunspell.algo.lookup import analyze
from spyll.hunspell.algo.lookup import CompoundPos

dic = Dictionary.from_folder('tests/fixtures/hunspell-orig/opentaal_keepcase')

# print(dic.aff.pfx)
# print(list(analyze(dic.aff, dic.dic, 'foo-bar')))
# print(dic.lookup('foo-baz'))
# print(list(analyze(dic.aff, dic.dic, 'foo-baz')))
# data = list(dic.analyzer.word_forms('arbeit', compoundpos=CompoundPos.END))
# print('----')
# print(data)

print(dic.lookup("Computerarbeits-computer"))

data = list(dic.analyzer.analyze("Computerarbeits-computer"))

for var in data:
    print()
    print('---------')
    for form in var:
        print(form)


# print(list(analyze(dic.aff, dic.dic, 'implied')))

