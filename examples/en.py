import time

from spyll.hunspell.dictionary import Dictionary

d = Dictionary('dictionaries/en_US')

# print(d.lookup('chickpeas'))
print(d.lookup('incited'))
print(d.lookup('21st'))
t = time.time()
print(d.lookup('verylongsomethingwillyoucheckme'))
print(time.time() - t)
