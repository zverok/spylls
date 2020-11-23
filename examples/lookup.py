import re
import os.path

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo.capitalization import Type as CapType

dic = Dictionary.from_files('dictionaries/en_US')

print(*dic.lookuper.good_forms('building'))
print(*dic.lookuper.good_forms('111th'))

print(*dic.lookuper.affix_forms('reboots', captype=CapType.NO))
