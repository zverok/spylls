``spylls.hunspell``: details and code
=====================================

How Hunspell works
-------------------

Hunspell spellchecker (like any other spellchecker, in fact) has two main functions: check if a word is correct (**lookup**), and, for a misspelled word, provide a hypothesis of what it might be corrected to (**suggest**).

**Lookup** may seem simple: just take a list of known words and check if the input is included in this list. But this list-based approach ignores some important concerns:

* In `Synthetic languages <https://en.wikipedia.org/wiki/Synthetic_language>`_, one word can have *many forms*. In English, the verb "create" have only those forms: "creates", "creating", and "created"; but in Ukrainian, the same verb "створювати" has dozens, depending on tense, the gender of the speaker, and other factors. One still could store a flat list of all possible forms, but it can easily contain millions of entries, requiring severe optimizations of storage and lookup. Alternatively, the spellchecker can store word bases and possible affixes separately, tagging them with metainformation about which words can have which affixes—and that's what Hunspell does;
* Many languages (like German) have *word compounding*: valid words can be glued together to create new words, by special rules, and all of those new words would be valid. In these languages, the dictionary just can't list all possible valid words, and the spellchecker needs to break a word into parts and analyze them separately;
* Other complications, like word casing (both "kitten" and "Kitten" are valid, but lowercase "london" is not)
* Interconnectedness of all concerns above ("this suffix is allowed at the end of the compound words only, but not if the word is capitalized")

To **suggest**, the spellchecker can:

* either try to *mutate* the misspelled word (remove letters, add letters, swap them, etc) and see if the resulting word is a "good" one;
* or, calculate the *similarity* of the misspelled word to the words in the dictionary, and chose the most similar ones.

Either approach is complicated by the facts described in lookup: it is ineffective (and sometimes impossible) to list "all valid words", and not always easy to check if the word is correct.

Hunspell does both, on the different stages of its suggestion algorithm, and does some optimization so that process wouldn't take forever.

Data formats and algorithms
---------------------------

Every Hunspell dictionary consists of two text files:

* ``<languagename>.dic`` (called ".dic file" further), containing words + some metainformation ("flags" and "data tags");
* ``<languagename>.aff`` (called ".aff file" further), defining flag meanings ("word with this flag can have this suffix", "...can be at the end of compound words", "...should never be suggested" etc.), and a lot of other spellchecking settings, like "what characters allowed in words", "what types of suggestions are allowed", etc.

On **lookup**, Hunspell does several cycles:

* check the full word itself, if it is already in the dictionary (to complicate matters even further, some words can be marked with ``NEEDSAFFIX`` flag, so they aren't correct without affixes)
* look through all affixes (suffixes and prefixes), and checks if the word can be split into known affixes and known stem (and this stem is allowed to have those affixes)
* if the dictionary settings allow that, try to split the word into several, and analyze if it is a compounding of several stems and affixes

On **suggest**, Hunspell does roughly this:

* tries several different *permutations* of the misspelled word and looks if they would produce valid words;
* calculates misspelled words similarity to all dictionary stems, and of the most similar stems tries to find the most similar forms with affixes;
* (if the .aff file includes phonetic information) tries to find stems by phonetical similarity to misspelled words.

Code walkthrough
----------------

Note that all the code is extensively commented, and the "Show code" link is embedded into all method docs, so you can read the relevant code in-place.

.. toctree::
   :maxdepth: 2

   hunspell/data_dic
   hunspell/data_aff
   hunspell/file_readers
   hunspell/readers_dic
   hunspell/readers_aff
   hunspell/algo_lookup
   hunspell/algo_suggest
   hunspell/algo_capitalization
   hunspell/algo_string_utils
   hunspell/algo_trie
