Spyll tests
===========

Unit tests
----------

Currently, there aren't much of those. Some drafts are in ``tests/unit``, but they are outdated. At the moment, I use integrational tests to check if anything broken.

Integrational tests
-------------------

"Integrational" tests are using Hunspell's `tests files <https://github.com/hunspell/hunspell/tree/master/tests>`_ which are structured this way:

* ``<name>.aff`` and ``<name>.dic`` -- dictionary definition
* ``<name>.good`` -- words that should be considered good
* ``<name>.wrong`` -- words that should be considered wrong
* ``<name>.sug`` -- what should be suggested instead of the wrong words

To run Spyll's tests against those, you can run ``poetry run python tests/integrational/test_lookup.py`` and ``poetry run python tests/integrational/test_suggest.py``, which produce quite friendly reports.

Changes made to Hunspell fixtures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Basically, ``tests/integrational/fixtures/`` contain all tests from Hunspell repo, with the changes described below.

Add test cases:

* ``checksharps.good`` -- add word ``AUSSTOß`` (actually, there was no proper test for ``CHECKSHARPS`` behavior...)
* ``nosplitsugs`` -- add whole fixture set (test for ``NOSPLITSUGS`` directive)

Add empty lines: Hunspell's tests just check "entire list of suggestions" vs "entire list of expected suggestions"; Spyll's is more fine-grained and test line-by-line (for this word, that suggestion expected), it requires correspondence of lines in ``*.wrong`` o those in ``*.sug``, so when for some "wrong" word there should be no suggestions, ``*.sug`` file should contain an empty line. Such changes were added to:

* ngram_utf_fix.sug
* opentaal_forbiddenword1.sug
* opentaal_forbiddenword2.sug
* ph2.sug

Finally, one small change is in ``phone.sug`` (metaphone-based suggestion), related to the fact that several suggestions have exactly the same score, and which ones of them to return is depends only on Python/C sorting difference.


