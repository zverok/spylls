import time

from spyll.hunspell import Dictionary

t1 = time.time()

d = Dictionary.from_folder('dictionaries/ru_RU')

t2 = time.time()
print(f"loaded in {t2-t1}")

print(d.lookup('красоток'))

t3 = time.time()
print(f"search in {t3-t2}")
