from spyll.hunspell.dictionary import Dictionary

d = Dictionary('dictionaries/ru_RU')

for r in d.lookup('апельсиновые'):
    print(r)
