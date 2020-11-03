import re
import os.path

from spyll.hunspell.dictionary import Dictionary
# from spyll.hunspell.algo.lookup import analyze
from spyll.hunspell.algo.lookup import CompoundPos

dic = Dictionary.from_files('tests/integrational/fixtures/germancompoundingold')

print(*dic.lookuper.good_forms('Computern'))
