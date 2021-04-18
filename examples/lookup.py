import pathlib
path = pathlib.Path(__file__).parent  / 'en_US'

from spylls.hunspell.dictionary import Dictionary
from spylls.hunspell.algo.capitalization import Type as CapType

dictionary = Dictionary.from_files(str(path))

print([*dictionary.lookuper.good_forms('building')])
print([*dictionary.lookuper.good_forms('111th')])

print(*dictionary.lookuper.affix_forms('reboots', captype=CapType.NO))
