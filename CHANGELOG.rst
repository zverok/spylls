Changelog
=========

0.1.2 (unreleased)
------------------

* Fix #4 (sorting fail in ``ngram_suggest``)
* Fix Dutch ``IJ`` edge case processing
* Fix edge case for suffix conditions loading (manifested on LibreOffice sv_SE dictionary)
* Fix #7 (loading of morphology aliases)
* Bundle SCOWL en_US dictionary with Spylls for easier showcasing/experimenting
* Improve docs
* Significantly fix suggestion algorithm (simplify, and implement suggestion count limitation)
