Spyll: Hunspell ported to Python
================================

**Spyll** is an effort of porting prominent spellcheckers into clear, well-structured, well-documented Python. It is inteded to be useful both as a library and as some kind of "reference (or investigatory, if you will) implementation". Currently, only `Hunspell <https://github.com/hunspell/hunspell>`_ is ported.

Reasons
-------

Spellchecking is a notoriously hard task that looks easy. The MVP everybody starts from is "just look if the word in the known list, and if it is not, calculate Levenstein distance to know what's the most similar one and suggest it", but things get complicated very quickly once you start working with real texts, and languages other than English.

There are some modern approaches to spell and grammar checking, which are base on machine learning, can recognize context and do a lot of other interesting stuff. But "classic", dictionary-based spellcheckers are still most widespread solution, with **hunspell** being the most widespread of all. It is embedded into Chrome, Firefox, OpenOffice, Adobe's products, Linux and MacOS distributions; there are Hunspell-compatible dictionaries for most of human languages.

At the same time, hunspell is long-living, complicated, almost undocumented piece of software, and it was our feeling that the significant part of human knowledge is somehow "locked" in a form of large C++ project. That's how **spyll** was born: as an attempt to "unlock" it, via well-structured and well-documented implementation in high-level language.

Design choices
--------------

* **Spyll** is implemented in Python, as a most widespread high-level language of 2020s (besides EcmaScript, but I just can't do it... for personal reasons);
* The code is as "vanilla Python" as possible, so it should be reasonable readable for developer in any modern language; the most Python-specific feature used is method returning generators (instead of arrays);
* Code is structured in a (reasonably) low amount of classes with (reasonably) large methods, exposing the imperative nature of hunspell algorithms; probably "very OO" or "very functional" approach could've made code more appealing for some, but I tried to communicate the algorithms themselves (for possible reimplementations in other languages and architectures), not my own views on how to code;
* ...At the same time, it doesn't try to reproduce Hunspell's structure of classes, method names and calls, but rather express "what it does" in the most simple/straightforward ways

Usage as a library
------------------

.. code-block:: python

  from spyll.hunspell import Dictionary

  # from folder where en_US.aff and en_US.dic are present
  dictionary = Dictionary.from_files('/path/to/dictionary/en_US')
  # or, from Firefox/LibreOffice dictionary extension
  dictionary = Dictionary.from_archive('/path/to/dictionary/en_US.odt')
  # or, from system folders (on Linux)
  dictionary = Dictionary.from_system('en_US')

  print(dictionary.lookup('spyll'))
  # False
  for suggestion in dictionary.suggest('spyll'):
    print(sugestion)
  # spell
  # spill
  # spy ll
  # spy-ll

See :class:`Dictionary <spyll.hunspell.dictionary.Dictionary>` class docs for more details.

.. toctree::
   :maxdepth: 2

   hunspell/dictionary


Reading the code
----------------

.. toctree::
   :maxdepth: 2

   hunspell


Completeness
------------

Generally, spyll thrives for the *full* port, handling all possible quirks and rare options, that's the idea of the project. (Would be rather easy to make dictionary reader + word lookup working for most simple cases, but that wouldn't demonstrate the complexity and interlinkedness of the task.)

Current state of the port:

* Only lookup (whether word in the dictionary) and suggest (for misspelled words) are ported; it means no morphological analysis (which some dictionaries allow), and no tokenization of source text (Python has enough libraries for that)
* Of known directives, X are supported, the rest is silently ignored (none of those are used in the dictionaries available in Firefox or LibreOffice repositories)
* Of hunspell's lookup tests, X are successful, 6 are pending (due to the same rare form of COMPOUNPATTERN directive, which used in no humanly known dictionary), and 1 is failing (ironically as it is, Hungarian one, which in the original Hunspell is handled by several exceptional branches with explicit "if this is hungarian..." clauses)
* Of hunspell's suggest tests, X are failing and Y pending
* spyll is confirmed to at least read successfully all dictionaries available in Firefox and LibreOffice official dictionary repositories

So, it is, like ~80% theoretically complete and ~95% pragmatically complete.

Performance
-----------

It is not stellar, neither completely unusable (YMMV).

* Dictionary reading is avg (linearly dependent on dictionary size)
* Lookup is (...)
* Suggest is (up to ... for ...)

I believe that significantly better performance is hard/impossibe to achieve *in pure Python*, preserving the *straightforward port of the algorithms*. As clear representation of algorithm is the *main* goal, I am leaving it at that. Appropriate data structures are chosen when necessary (the most non-trivial example is trie for affixes), and code is profiled thoroughly to remove bottlenecks that were hanging low (lost in metaphor, sorry). Maybe overuse of ``re`` might be rethought a bit.

Q&A
---

Why all the code is namespaced under ``spyll.hunspell`` (and not just ``spyll``)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to author's delusion of grandeur! I plan/hope/dream it will once include not only Hunspell's "explanatory ports", but for some other spellcheckers, too

Why all the complexity if Peter Norvig's `spellchecker <https://norvig.com/spell-correct.html>`_ is just 36 lines of Python?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TBD

Where do I get the dictionaries?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TBD

Other ports
-----------

Here only "pure" ports of Hunspell to other languages are listed, not wrappers around the original hunspell (of which there are plenty):

* .NET: `WeCantSpell <https://github.com/aarondandy/WeCantSpell.Hunspell>`_
* JS: `nspell <https://github.com/wooorm/nspell>`_ (only some directives)
* C++: `nuspell <https://github.com/nuspell/nuspell>`_ (weirdly, pretends to be independent project with no relations to anything, while at the same time seeming to support the same format of aff/dic, and striving to conform to hunspell's test suite)

Some other approaches to spellchecking
--------------------------------------

* `aspell <https://github.com/GNUAspell/aspell>`_, while being in some sense a "grandparent" of Hunspell, is said to `sometimes provide better suggestions <https://battlepenguin.com/tech/aspell-and-hunspell-a-tale-of-two-spell-checkers/>`_;
* `morphologik <https://github.com/morfologik/morfologik-stemming>`_: stemmer/POS-tagger/spellchecker used by `LanguageTool <https://languagetool.org/>`_; it uses very interesting technique of encoding dictionaries with FSA, making dictionary lookup much more effective than Hunspell's;
* `voikko <https://voikko.puimula.org/>`_, developed for Finnish, which Hunspell can't handle too well due to its complicated affixes;
* `SymSpell <https://github.com/wolfgarbe/SymSpell>`_: very fast algorithm (relying on availability of full list of all language's words)
* `JamSpell <https://github.com/bakwc/JamSpell>`_: machine learning-based one
