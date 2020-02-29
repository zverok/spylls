import time

from spyll.hunspell.dictionary import Dictionary

t1 = time.time()

d = Dictionary('dictionaries/ru_RU')

t2 = time.time()
print(f"loaded in {t2-t1}")

for r in d.lookup('красоток'):
    print(r)

t3 = time.time()
print(f"search in {t3-t2}")
