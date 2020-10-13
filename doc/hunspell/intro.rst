Lookup
======

The simplest dictionary lookup (just have a flat list of "good" words and look through them) might be considered not enough for lot of languages.

Hunspell supports:
* Word inflexions
* Word compounding

"Flags" mechanism also used to mark word forms that are logically possible yet incorrect; to mark words whose capitalization shouldn't change, word stems that definitely need affix and so on.

Generally, word lookup works this way:
* Preprocess (Iconv, ignore)
* Check this form
* Deaffix and check all possible forms
* Split into valid compound parts and check all the forms

Suggest
=======

* Apply known transformations
* Search through entire dictionary with ngram comparison
* (Sometimes) search through metaphones
