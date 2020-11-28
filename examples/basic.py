import pathlib
path = pathlib.Path(__file__).parent  / 'en_US'

from spyll.hunspell import Dictionary

dictionary = Dictionary.from_files(str(path))

print(dictionary.lookup('spell'))
print(dictionary.lookup('spyll'))
print([*dictionary.suggest('spyll')])
