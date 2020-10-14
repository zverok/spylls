**Spyll** is an effort of porting prominent spellcheckers into clear, well-structured, well-documented Python. It is inteded to be useful both as a library and as a "reference implementation". Currently, only `Hunspell <https://github.com/hunspell/hunspell>`_ is ported.

Reasons
=======

Spellchecking is a notoriously hard task that looks easy. It consists of a) checking, whether the word is in the dictionary and b) if it is not, suggesting what the correct form might be.

Even (a) is "easy" (look through the list of known correct words) only for some languages, like English. For others, having rich word forms (say, Slavic ones) or word compounding (like German), requires either millions of word forms prepared, or non-trivial word analysis logic.

The second task (suggestion) is even trickier. TODO

While there are some modern approaches to spell and grammar checking, which are base on machine learning, can recognize context and do a lot of other interesting stuff, "classic", dictionary-based spellcheckers are still most widespread solution, with **hunspell** being the most widespread of all. It is embedded into Chrome, Firefox, OpenOffice, Adobe's products, Linux and MacOS distributions... At the same time, hunspell is long-living, complicated, almost undocumented piece of software, which

Usage as a library
==================

.. code-block:: python

  from spyll.hunspell import Dictionary

  # from folder where en_US.aff and en_US.dic are present
  dictionary = Dictionary.from_files('/path/to/dictionary/en_US')
  # or, from Firefox/LibreOffice dictionary extension
  dictionary = Dictionary.from_archive('/path/to/dictionary/en_US.odt')
  # or, from system folders (on Linux)
  dictionary = Dictionary.from_system('en_US')

  dictionary.lookup('spyll') # False

  list(dictionary.suggest('spyll')) # ['spell', 'spill', 'spy ll', 'spy-ll']

See `Dictionary class docs <TODO>`_ for more details.


Design goals
============

Reading the code
================

Modules inside ``spyll/hunspell`` folder (except for small public interface of the ``Dictionary``) are written in a style akin to literate programming (explanations interweaved with code in supposedly readable manner). They could be read right in the GitHub (or your preferred code editor), but we suggest a rendering on `the dedicated site <https://spyll.github.io/hunspell/code>`_.

* It is suggested that you start from hunspell concepts explanations
* data.aff and data.dic modules declare data structures (data.aff also provides **very** thorough explanation of each and every directive, and points where in code they are used)
* algo.lookup defines the lookup algorithm (with compound word breaking extracted into algo.compounding)
* algo.suggest defines the suggestion algorithm, of which ngram-based suggestions are detailed in algo.ngram_suggest, and phonetics-based suggestion in algo.phonet


Completeness
============

Generally, spyll thrives for the *full* port, handling all possible quirks and rare options, that's the idea of the project. (Would be rather easy to make dictionary reader + word lookup working for most simple cases, but that wouldn't demonstrate the complexity and interlinkedness of the task.)

Current state of the port:

* Only lookup (whether word in the dictionary) and suggest (for misspelled words) are ported; it means no morphological analysis (which some dictionaries allow), and no tokenization of source text (Python has enough libraries for that)
* Of known directives, X are supported, the rest is silently ignored (none of those are used in the dictionaries available in Firefox or LibreOffice repositories)
* Of hunspell's lookup tests, X are successful, 6 are pending (due to the same rare form of COMPOUNPATTERN directive, which used in no humanly known dictionary), and 1 is failing (ironically as it is, Hungarian one, which in the original Hunspell is handled by several exceptional branches with explicit "if this is hungarian..." clauses)
* Of hunspell's suggest tests, X are failing and Y pending
* spyll is confirmed to at least read successfully all dictionaries available in Firefox and LibreOffice official dictionary repositories

So, it is, like ~80% theoretically complete and ~95% pragmatically complete.

Performance
===========

It is not stellar, neither completely unusable (YMMV).

* Dictionary reading is avg (linearly dependent on dictionary size)
* Lookup is (...)
* Suggest is (up to ... for ...)

I believe that significantly better performance is hard/impossibe to achieve *in pure Python*, preserving the *straightforward port of the algorithms*. As clear representation of algorithm is the *main* goal, I am leaving it at that. Appropriate data structures are chosen when necessary (the most non-trivial example is trie for affixes), and code is profiled thoroughly to remove bottlenecks that were hanging low (lost in metaphor, sorry). Maybe overuse of ``re`` might be rethought a bit.

Q&A
===

Why ``spyll.hunspell``?

Delusion of grandeur

What about Norvig's?

Where do I get the dictionaries?

Other ports
===========

Here only "pure" ports of Hunspell to other languages are listed, not wrappers around the original hunspell (of which there are plenty):

* .NET: `WeCantSpell <https://github.com/aarondandy/WeCantSpell.Hunspell>`_
* JS: `nspell <https://github.com/wooorm/nspell>`_ (only some directives)
* C++: `nuspell <https://github.com/nuspell/nuspell>`_ (weirdly, pretends to be independent project with no relations to anything, while at the same time seeming to support the same format of aff/dic, and striving to conform to hunspell's test suite)

Other approaches to spellchecking
=================================

* aspell
* morphologik
* voikko
* SymSpell

Author and license
==================
