Changelog
=========

0.1.5 - 2021-05-12
------------------

* Fix bug in loading some dictionary affixes
* Bundle ``unmunch.py`` script (naive, more like a demo)
* Add Patreon link :)

0.1.4 - 2021-02-10
------------------

* Add ``PHONE`` table to English dictionary to demonstrate phonetical algorithms
* Enhance (or, rather, make it more Hunspell-alike) ngram suggestions in presence of ``PHONE`` definitions
* Simplify a bit


0.1.3 - 2021-01-28
------------------

* Fix bug in ``permutations.swapchars`` (it didn't work at all... funny how Hunspell's test suit never pointed at it)
* Return to Hunspell's way to produce edit suggestions: first, only non-compound ones, and then compound ones. Clever Spylls' "optimization" considered harmful
* Bundle a few more dictionaries to play with

0.1.2 - 2021-01-21
------------------

* Fix #4 (sorting fail in ``ngram_suggest``, manifested in Marathi dictionaries)
* Fix #7 (loading of morphology aliases, manifested in OpenTaal Dutch dictionaries)
* Fix Dutch ``IJ`` edge case processing
* Fix edge case for suffix conditions loading (manifested on LibreOffice sv_SE dictionary)
* Bundle SCOWL en_US dictionary with Spylls for easier showcasing/experimenting
* Significantly fix suggestion algorithm (simplify, and implement suggestion count limitation)
* Improve docs in a few places
