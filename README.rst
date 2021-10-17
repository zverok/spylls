Spylls: Hunspell ported to Python
=================================

**Spylls** is an effort of porting prominent spellcheckers into clear, well-structured, well-documented Python. It is intended to be useful both as a library and as some kind of "reference (or investigatory, if you will) implementation". Currently, only `Hunspell <https://github.com/hunspell/hunspell>`_ is ported.

Hunspell is a long-living, complicated, almost undocumented piece of software, and it was our feeling that the significant part of human knowledge is somehow "locked" in a form of a large C++ project. That's how **Spylls** was born: as an attempt to "unlock" it, via well-structured and well-documented implementation in a high-level language.

**Follow the explanatory blog post series:** `on my blog <https://zverok.github.io/spellchecker.html>`_, `on Medium <https://medium.com/spylls-rebuilding-the-spellchecker>`_, or `subscribe to my mailing list <https://zverok.github.io/subscribe.html>`_.

Usage as a library
------------------

::

  $ pip install spylls

.. code-block:: python

  from spylls.hunspell import Dictionary

  # en_US dictionary is distributed with spylls
  # See docs to load other dictionaries
  dictionary = Dictionary.from_files('en_US')

  print(dictionary.lookup('spylls'))
  # False
  for suggestion in dictionary.suggest('spylls'):
      print(suggestion)
  # spells
  # spills

Documentation
-------------

Full documentation, including detailed source code/algorithms walkthrough, more detailed reasoning and some completeness reports, is available at https://spylls.readthedocs.io/.

Project Links
-------------

- Docs: https://spylls.readthedocs.io/
- GitHub: https://github.com/zverok/spylls
- PyPI: https://pypi.python.org/pypi/spylls
- Issues: https://github.com/spylls/spylls/issues

License
-------

MPL 2.0. See the bundled `LICENSE <https://github.com/spylls/spylls/blob/master/LICENSE>`_ file for more details.
Note that being an "explanatory rewrite", spylls should considered a derivative work of Hunspell, and so would be all of its ports/rewrites.

We are incredibly grateful to Hunspell's original authors and current maintainers for all the hard work they've put into the most used spellchecker in the world!
