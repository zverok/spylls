import pathlib
path = pathlib.Path(__file__).parent  / 'en_US'

from spyll.hunspell import Dictionary

dictionary = Dictionary.from_files(str(path))

print(dictionary.lookup('spells'))
print(dictionary.lookup('spylls'))
print([*dictionary.suggest('spylls')])
