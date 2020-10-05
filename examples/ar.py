import time

from spyll.hunspell.dictionary import Dictionary
from spyll.hunspell.algo import suggest

# t = time.time()
d = Dictionary.from_folder('/home/zverok/projects/1foreign/LibreOffice-dictionaries/ar/ar')
# print(f'Loading: {time.time() - t}')

# t = time.time()
# print(d.lookup('chickpeas'))
# print(d.lookup('العربية'))
# print(f'Normal lookups: {time.time() - t}')

# t = time.time()
# print(list(d.suggest('العربية')))
# print(f'Suggest: {time.time() - t}')


# print(list(suggest.suggest_debug(d, 'العربية')))
