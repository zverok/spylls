Spylls: Hunspell ported to Python
=================================

**Spylls** is an effort of porting prominent spellcheckers into clear, well-structured, well-documented Python. It is inteded to be useful both as a library and as some kind of "reference (or investigatory, if you will) implementation". Currently, only `Hunspell <https://github.com/hunspell/hunspell>`_ is ported.

Hunspell is long-living, complicated, almost undocumented piece of software, and it was our feeling that the significant part of human knowledge is somehow "locked" in a form of large C++ project. That's how **spylls** was born: as an attempt to "unlock" it, via well-structured and well-documented implementation in high-level language.

Usage as a library
------------------

::

  $ pip install spylls

.. code-block:: python

  from spylls.hunspell import Dictionary

  # from folder where en_US.aff and en_US.dic are present
  dictionary = Dictionary.from_files('/path/to/dictionary/en_US')
  # or, from Firefox/LibreOffice dictionary extension
  dictionary = Dictionary.from_archive('/path/to/dictionary/en_US.odt')
  # or, from system folders (on Linux)
  dictionary = Dictionary.from_system('en_US')

  print(dictionary.lookup('spylls'))
  # False
  for suggestion in dictionary.suggest('spylls'):
    print(sugestion)
  # spell
  # spill
  # spy ll
  # spy-ll

Documentation
-------------

Full documentation, including detailed source code/algorithms walkthrough, more detailed reasoning and some completeness reports, is available at https://spylls.readthedocs.io/.

Project Links
-------------

- Docs: https://spylls.readthedocs.io/
- PyPI: https://pypi.python.org/pypi/spylls
- Issues: https://github.com/spylls/spylls/issues

License
-------

MIT licensed. See the bundled `LICENSE <https://github.com/spylls/spylls/blob/master/LICENSE>`_ file for more details.
