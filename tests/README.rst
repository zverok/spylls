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

Basiclly, ``tests/integrational/fixtures/`` contain all tests from Hunspell repo, with the changes described below.

Add test cases:

* ``checksharps.good`` -- add word ``AUSSTOß`` (actually, there was no proper test for ``CHECKSHARPS`` behavior...)
* ``nosplitsugs`` -- add whole fixture set (test for ``NOSPLITSUGS`` directive)

Add empty lines: Hunspell's tests just check "entire list of suggestions" vs "entire list of expected suggestions"; Spyll's is more fine-grained and test line-by-line (for this word, that suggestion expected), it requires correspondence of lines in ``*.wrong`` o those in ``*.sug``, so when for some "wrong" word there should be no suggestions, ``*.sug`` file should contain an empty line. Such changes were added to:

* ngram_utf_fix.sug
* opentaal_forbiddenword1.sug
* opentaal_forbiddenword2.sug
* ph2.sug

Next set of changes related to the fact that Spyll's approach to suggest is a bit simpler than Hunspells, as explained in ``Suggest`` class docs:

  In Hunspell, all permutations-based logic is run twice: first, checks if any of the permutated variants
  is a valid non-compound word; then (if nothing good was found), for all the same permutations, checks
  if maybe it is a valid compound word. It is done this way because checking whether word is correct
  *not regarding compounding* is much faster. We ignore this optimization in the name of clarity
  of the algorithm -- and on the way make suggestions better in edge cases: when compound and non-compound
  word are accidentally joined, Hunspell can't sugest to split them (try with "11thhour": "11th" is
  compound word in English dictionary, and hunspell wouldn't suggest "11th hour", but Spyll would).

So, Spyll's suggest is actually better! Changes related to it are introduced in:

* opentaal_forbiddenword1.sug
* opentaal_forbiddenword2.sug
* ph2.sug

Finally, one small change is in ``phone.sug`` (metaphone-based suggestion), related to the fact that several suggestions have exactly the same score, and which ones of them to return is depends only on Python/C sorting difference.


