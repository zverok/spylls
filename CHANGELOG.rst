Changelog
=========

0.1.2 (unreleased)
------------------

* Fix #4 (sorting fail in ``ngram_suggest``, manifested in Marathi dictionaries)
* Fix #7 (loading of morphology aliases, manifested in OpenTaal Dutch dictionaries)
* Fix Dutch ``IJ`` edge case processing
* Fix edge case for suffix conditions loading (manifested on LibreOffice sv_SE dictionary)
* Bundle SCOWL en_US dictionary with Spylls for easier showcasing/experimenting
* Significantly fix suggestion algorithm (simplify, and implement suggestion count limitation)
* Improve docs in a few places
