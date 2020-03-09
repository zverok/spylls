This site tries to gather all the humanity's knowledge about open-source spellchecking.

There is 2 stages in spellchecking (or 3, depends on how you count):

0. Split the text into words
1. Check if the word is correct
2. Suggest how to fix this word

**Splitting** seems to not be related to the spellchecking problem directly, but there are things to consider:
* languages with punctuation being part of the word or being just punctuation
* suggestion: imagine text with "im agine" in it: if the spellchecker is aware of the whole text, it can correctly propose "im agine"→"imagine" fix, but if it is fed text word-by-word, it can't.

**Dictionary lookup**: "the simplest thing that could possibly work" approach is:
* make just a long list of all correct words in the language
* check if the word in this list

The approach kinda "works" for lightly flexed languages like English, but poses many problems for other languages:
* for languages with powerful flexing (for example, Slavic ones), one root can produce tens or hundreds of forms: "cat" in Ukrainian is "кіт", but it has this forms: кота, котом, коту, коти, котами... (note also change of vowel і→о in word forms) and derivative words (one may count them as independent one, or as same root + differnt suffixes) like "котів" ("cat's") and so on. You still can list "all known forms of all known words", but the list would easily have millions of words and requires some memory-effective algorithms to store and performance-effective algorithms to search
* agglutinative languages (like German)
* "unknown but valid" words problem: once you assume "гугл" is a valid word, "гуглить", "загуглить", "выгугленный" all understandable for native reader and may be "valid" from point of view of the author

The question "what is the dictionary" itself isn't that easy either: depending on the circumstances, one might vary their expectations of spellchecker from "consider 'crap' a typo, it is a formal document and I probably mistyped 'crab'" to "it is chat, every slang is acceptable but please fix my 'ya dowg' to 'yo dawg'". When we consider also suggestions, "what's the dictionary" problem becomes even more tricky.

**Suggestion** is the most peculiar. Generally, from "wrong" word, we need to try guessing what it might be. The problems include:
* how many guesses should we produce?
* how to order those guesses?
