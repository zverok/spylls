import re
import os.path

from spylls.hunspell.algo import capitalization as cap

regular = cap.Casing()

print(regular.guess('Paris'))

print(regular.lower('Izmir'))
print(regular.upper('Izmir'))

turkic = cap.TurkicCasing()

print(turkic.lower('Izmir'))
print(turkic.upper('Izmir'))

german = cap.GermanCasing()

print(german.lower('STRASSE'))
