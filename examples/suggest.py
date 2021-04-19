import pathlib
path = pathlib.Path(__file__).parent  / 'en_US'

from spylls.hunspell.dictionary import Dictionary

dictionary = Dictionary.from_files(str(path))

suggest = dictionary.suggester

for suggestion in suggest.suggestions('spylls'):
    print(suggestion)
