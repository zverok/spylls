import re
import os.path

from spyll.hunspell.dictionary import Dictionary

dic = Dictionary.from_files('dictionaries/en_US')

print(*dic.lookuper.good_forms('building'))
print(*dic.lookuper.good_forms('111th'))
