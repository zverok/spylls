The folder contains some examples of ``spyll`` usage.

**To use it as a library** (only lookup/suggest), all you need is demonstrated in ``basic.py``: Basic usage of ``spylls.hunspell.Dictionary`` (external API) for lookup and suggest

**Access to some internal objects** is demonstrated in:

* ``dic.py``: ``Dic`` (representation of wordlist file)
* ``lookup.py``: experiments with ``Lookup`` object (word search/form production algorithm)
* ``lookup.py``: experiments with ``Suggest`` object (suggest correction for misspelled word)
* ``utils.py``: demonstrates how some utility classes work
