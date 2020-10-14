from spyll.hunspell import Dictionary

d = Dictionary.from_system('en_US')

print(list(d.suggest('spyll')))
