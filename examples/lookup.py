import pathlib
path = pathlib.Path(__file__).parent  / 'en_US'

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo.capitalization import Type as CapType

dictionary = Dictionary.from_files(str(path))

print([*dictionary.lookuper.good_forms('building')])
print([*dictionary.lookuper.good_forms('111th')])

print(*dictionary.lookuper.affix_forms('reboots', captype=CapType.NO))
