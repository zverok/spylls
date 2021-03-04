Spylls: Hunspell ported to Python
=================================

**Spylls** is an effort of porting prominent spellcheckers into clear, well-structured, well-documented Python. It is intended to be useful both as a library and as some kind of "reference (or investigatory, if you will) implementation". Currently, only `Hunspell <https://github.com/hunspell/hunspell>`_ is ported.

**Follow the explanatory blog post series:** `on my blog <https://zverok.github.io/spellchecker.html>`_, `on Medium <https://medium.com/spylls-rebuilding-the-spellchecker>`_, or `subscribe to my mailing list <https://zverok.github.io/subscribe.html>`_.

Reasons
-------

Spellchecking is a notoriously hard task that looks easy. The MVP everybody starts from is "just look if the word in the known list, and if it is not, calculate Levenstein distance to know what's the most similar one and suggest it", but things get complicated very quickly once you start working with real texts, and languages other than English.

There are some modern approaches to spell and grammar checking, which are based on machine learning, can recognize context, and do a lot of other interesting stuff. But "classic", dictionary-based spellcheckers are still the most widespread solution, with **Hunspell** being the most widespread of all. It is embedded into Chrome, Firefox, OpenOffice, Adobe's products, Linux, and macOS distributions; there are Hunspell-compatible dictionaries for most of the human languages.

At the same time, Hunspell is a long-living, complicated, almost undocumented piece of software, and it was our feeling that the significant part of human knowledge is somehow "locked" in a form of a large C++ project. That's how **Spylls** was born: as an attempt to "unlock" it, via well-structured and well-documented implementation in a high-level language.

Design choices
--------------

* **Spylls** is implemented in Python, as a most widespread high-level language of the 2020s (besides EcmaScript, but I just can't do it... for personal reasons);
* The code is as "vanilla Python" as possible, so it should be reasonably readable for a developer in any modern language; the most Python-specific feature used is a method returning generators (instead of arrays);
* Code is structured in a (reasonably) low amount of classes with (reasonably) large methods, exposing the imperative nature of Hunspell's algorithms; probably "very OO" or "very functional" approach could've made code more appealing for some, but I tried to communicate the algorithms themselves (for possible reimplementations in other languages and architectures), not my views on how to code;
* ...At the same time, it doesn't try to reproduce Hunspell's structure of classes, method names, and calls, but rather express "what it does" in the most simple/straightforward ways.

Usage as a library
------------------

.. code-block:: python

  from spylls.hunspell import Dictionary

  # en_US dictionary is distributed with spylls
  # See docs to load other dictionaries
  dictionary = Dictionary.from_files('en_US')

  print(dictionary.lookup('spylls'))
  # False
  for suggestion in dictionary.suggest('spylls'):
      print(sugestion)
  # spells
  # spills

See :class:`Dictionary <spylls.hunspell.dictionary.Dictionary>` class docs for more details.

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

Generally, **Spylls** strives for the *full* port, handling all possible quirks and rare options, that's the idea of the project. (Would be rather easy to make dictionary reader + word lookup working for most simple cases, but that would bring no value.)

The current state of the port:

* Two main features of Hunspell are implemented: lookup (whether a word in the dictionary) and suggest (for misspelled words). It means no morphological analysis (which some dictionaries allow), and no tokenization of source text (Python has enough libraries for that)
* All known directives are at least *read* successfully; almost all of them are used in code where relevant (see :class:`Aff <spylls.hunspell.data.aff.Aff>` directive comments to see which are not); those that aren't (fully) implemented, are either very rare (not used in any known dictionary) and cumbersome, or related to aspects of Hunspell we don't implement (tokenization);
* Of **107** Hunspell's lookup tests, **6 are "pending"**: 5 due to the same rare form of :attr:`CHECKCOMPOUNDPATTERN <spylls.hunspell.data.aff.Aff.CHECKCOMPOUNDPATTERN>` directive, which used in no humanly known dictionary, and, ironically as it is, Hungarian one, which in the original Hunspell is handled by several exceptional branches with explicit "if this is Hungarian..." clauses
* Of **34** Hunspell's suggest tests, **3 are "pending"** (mostly due to handling of dots, which is related to tokenization)
* spylls is confirmed to at least read successfully all dictionaries available in Firefox and LibreOffice official dictionary repositories

So, it is, like ~80% theoretically complete and ~95% pragmatically complete.

On the other hand, I haven't used it extensively in a large production project or tried to spellcheck large texts in all supported languages, so there still might be some weird behavior in edge cases, not covered by Hunspell's tests. Also, it should be noted there are a lot of ``TODO:`` and ``FIXME:`` in the code, frequently signifying places where Hunspell's code was more complicated (simplifications not manifesting in failing tests, but probably slightly changing edge case behavior).

Performance
-----------

It is not stellar, neither completely unusable (YMMV). On my laptop ancient ThinkPad Edge E330 with i5-3210M CPU and 8 GiB of RAM:

* Dictionary reading for ``en_US`` is ~1.2s
* Lookup takes microseconds
* Suggest takes ~0.05s in good case, and up to 0.5s in a bad one (ngram suggest, which includes whole dictionary iteration)

I believe that significantly better performance is hard/impossible to achieve *in pure Python*, preserving the *straightforward port of the algorithms*. As the clear representation of the algorithm is the *main* goal, I am leaving it at that. Appropriate data structures are chosen when necessary (the most non-trivial example is trie for affixes), and code is profiled to remove bottlenecks that were hanging low (lost in metaphor, sorry). Maybe overuse of ``re`` might be rethought a bit.

Q&A
---

Why all the code is namespaced under ``spylls.hunspell`` (and not just ``spylls``)?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Due to the author's delusion of grandeur! I plan/hope/dream it will once include not only Hunspell's "explanatory ports", but for some other spellcheckers, too (for example, ``voikko`` and ``morfologik`` both look interesting in different approaches they take).

Why all the complexity if Peter Norvig's `spellchecker <https://norvig.com/spell-correct.html>`_ is just 36 lines of Python?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Actually, what Norvig's implementation is demonstrating is *one of the possible approaches to suggestion*. To work, it assumes that a full list of words for a given language is existing, finite, and has reasonable size; to work well, it requires having a weighted wordlist. Basically, it is an algorithm for spell suggestion which works for English, if you prepared a word list well (and even then, you might be surprised with some suggestions). Hunspell (and Spylls) works for dozens of languages with pre-existing dictionaries, but in order to do so, it is required to be times more complicated.

Where do I get the dictionaries?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The main sources of Hunspell-compatible dictionaries are `Firefox dictionaries <https://addons.mozilla.org/en-US/firefox/language-tools/>`_, `LibreOffice Dictionaries <https://extensions.libreoffice.org/?Tags%5B%5D=50>`_, `OpenOffice Dictionaries <https://extensions.openoffice.org/en/search?f%5B0%5D=field_project_tags%3A157>`_. All of those are downloadable as "extensions" (``.xpi`` for Firefox, ``.oxt`` for Libre/OpenOffice). "Extensions" are actually just ``.zip`` archives, which you can unpack and extract ``.aff``/``.dic`` files, but for convenience, Spylls can work with archives too:

.. code-block:: python

  >>> dictionary = Dictionary.from_zip('english_united_states_dictionary-68.0.xpi')

  >>> print(dictionary.lookup('spylls'))
  False


Other ports
-----------

Here only "pure" ports of Hunspell to other languages are listed, not wrappers around the original Hunspell (of which there are plenty):

* .NET: `WeCantSpell <https://github.com/aarondandy/WeCantSpell.Hunspell>`_
* JS: `nspell <https://github.com/wooorm/nspell>`_ (only some directives)
* C++: `nuspell <https://github.com/nuspell/nuspell>`_ (weirdly, pretends to be an independent project with no relations to anything, while at the same time seeming to support the same format of aff/dic, and striving to conform to Hunspell's test suite)

Some other approaches to spellchecking
--------------------------------------

* `aspell <https://github.com/GNUAspell/aspell>`_, while being in some sense a "grandparent" of Hunspell, is said to `sometimes provide better suggestions <https://battlepenguin.com/tech/aspell-and-hunspell-a-tale-of-two-spell-checkers/>`_;
* `morphologik <https://github.com/morfologik/morfologik-stemming>`_: stemmer/POS-tagger/spellchecker used by `LanguageTool <https://languagetool.org/>`_; it uses a very interesting technique of encoding dictionaries with FSA, making dictionary lookup much more effective than Hunspell's;
* `voikko <https://voikko.puimula.org/>`_, developed for Finnish, which Hunspell can't handle too well due to its complicated affixes;
* `SymSpell <https://github.com/wolfgarbe/SymSpell>`_: very fast algorithm (relying on the availability of a full list of all language's words)
* `JamSpell <https://github.com/bakwc/JamSpell>`_: machine learning-based one

Author
------

`Victor Shepelev <https://zverok.github.io>`_
