import time

from spyll.hunspell.dictionary import Dictionary

t = time.time()
d = Dictionary('dictionaries/en_US')
print(f'Loading: {time.time() - t}')

t = time.time()
print(d.lookup('chickpeas'))
print(d.lookup('incited'))
print(d.lookup('21st'))

print(f'Normal lookups: {time.time() - t}')

t = time.time()
print(d.lookup('verylongsomethingwillyoucheckme'))
print(f'Long lookup: {time.time() - t}')

t = time.time()
print(d.lookup('1234th'))
print(d.lookup('1234nd'))
print(f'Compound lookups: {time.time() - t}')

t = time.time()
# print(list(d.suggest('corupted')))
print(list(d.suggest('nachon')))
print(f'Suggest good: {time.time() - t}')

t = time.time()
print(list(d.suggest('crroapted')))
print(f'Suggest bad: {time.time() - t}')

print(list(d.suggest('hwihc')))
print(list(d.suggest('Hwihc')))

print(list(d.suggest('11thhour')))
