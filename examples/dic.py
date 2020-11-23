from spyll.hunspell import Dictionary

dictionary = Dictionary.from_files('dictionaries/en_US')

print(dictionary.dic)
print(dictionary.dic.homonyms('spell'))
