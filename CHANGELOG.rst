Changelog
=========

0.1.7 - 2021-01-23
------------------

* Simplify suffixes/prefixes checking, making it also more robust (Solving the `issues <https://github.com/zverok/spylls/issues/18#issuecomment-1013728978>`_ with modern Ukrainian dictionaries)


0.1.6 - 2021-10-17
------------------

* Fix several problems in code and comments pointed out by Daniel Höh (thanks!);
* Fix for single-letter words capitalization (thanks `@vletard <https://github.com/vletard>`_!);
* Change licence to MPL. It was `pointed <https://github.com/wooorm/nspell/issues/11#issuecomment-915802969>`_ to me that Spylls, being an "explantory rewrite" of Hunspell, can't have a permissive MIT license;
* Bundle ``unmunch.py`` script (now for real);
* Remove Patreon link, as Patreon's admins decided to demote me to "user" from "creator" for not posting my work on Patreon directly and not receiving any donations.

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
