"""

.. autofunction:: read_aff

.. autoclass:: Context
    :members:

Internal methods
^^^^^^^^^^^^^^^^

.. autofunction:: read_directive
.. autofunction:: read_value
.. autofunction:: make_affix

"""

import re
import itertools
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any, Iterable

from spylls.hunspell.data import aff

from spylls.hunspell.readers.file_reader import BaseReader


# Outdated directive names
SYNONYMS = {'PSEUDOROOT': 'NEEDAFFIX', 'COMPOUNDLAST': 'COMPOUNDEND'}

FLAG_LONG_REGEXP = re.compile(r'..')
FLAG_NUM_REGEXP = re.compile(r'\d+(?=,|$)')


@dataclass
class Context:
    """
    Class containing reading-time context necessary for reading both .aff and .dic file:
    encoding, flag format, chars to ignore.

    It is created in :meth:`read_aff` and then reused in :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>`.
    """

    #: Encoding of dictionary (see :attr:`Aff.SET <spylls.hunspell.data.aff.Aff.SET>`)
    encoding: str = 'Windows-1252'

    #: Flag format of dictionary (see :attr:`Aff.FLAG <spylls.hunspell.data.aff.Aff.FLAG>`)
    flag_format: str = 'short'

    #: List of flag synonyms (like ``1 => {'A', 'B', 'C'}``),
    #: see :attr:`Aff.AF <spylls.hunspell.data.aff.Aff.AF>`
    flag_synonyms: Dict[str, str] = field(default_factory=dict)

    #: Chars to ignore (see :attr:`Aff.IGNORE <spylls.hunspell.data.aff.Aff.IGNORE>`)
    ignore: Optional[aff.Ignore] = None

    def parse_flag(self, string: str) -> str:
        """
        Parse singular flag, considering attr:`flag_format`.
        """
        return list(self.parse_flags(string))[0]

    def parse_flags(self, string: str) -> Iterable[str]:
        """
        Parse set of flags, considering attr:`flag_format`.
        """

        if string is None:
            return []

        if self.flag_synonyms and string.isdigit():
            return self.flag_synonyms[string]

        # TODO: what if string format doesn't match expected (odd number of chars for long, etc.)?
        if self.flag_format == 'short':
            return string
        if self.flag_format == 'long':
            return FLAG_LONG_REGEXP.findall(string)
        if self.flag_format == 'num':
            return FLAG_NUM_REGEXP.findall(string)
        if self.flag_format == 'UTF-8':
            return string

        raise ValueError(f"Unknown flag format {self.flag_format}")


def read_aff(source: BaseReader) -> Tuple[aff.Aff, Context]:
    """
    Reads .aff file and creates an :class:`Aff <spylls.hunspell.data.aff.Aff>`.

    For each line calls :meth:`read_directive` (which either returns pair of ``(directive, value)``,
    or just skips the line).

    Args:
         source: "Reader" (thin wrapper around opened file or zipfile, targeting line-by-line reading)

    Returns:
        Aff itself and a :class:`Context` which then will be reused in
        :meth:`read_dic <spylls.hunspell.readers.dic.read_dic>`
    """

    data: Dict[str, Any] = {'SFX': {}, 'PFX': {}, 'FLAG': 'short'}
    context = Context()

    for (_, line) in source:
        dir_value = read_directive(source, line, context=context)
        if not dir_value:
            continue

        directive, value = dir_value

        # SFX/PFX are the only directives that have multiple entries in .aff file
        if directive in ['SFX', 'PFX']:
            data[directive][value[0].flag] = value
        else:
            data[directive] = value

        # Additional actions, changing further reading behavior
        if directive == 'FLAG':
            context.flag_format = value
        elif directive == 'AF':
            context.flag_synonyms = value
        elif directive == 'SET':
            context.encoding = value
            source.reset_encoding(value)
        elif directive == 'IGNORE':
            context.ignore = value

        if directive == 'FLAG' and value == 'UTF-8':
            # Weirdly enough, **flag type** ``UTF-8`` implicitly states the encoding is ``UTF-8`` too...
            context.encoding = 'UTF-8'
            data['SET'] = 'UTF-8'
            source.reset_encoding('UTF-8')

    return (aff.Aff(**data), context)   # type: ignore


def read_directive(source: BaseReader, line: str, *, context: Context) -> Optional[Tuple[str, Any]]:
    """
    Try to read directive from the next line, delegating value parsing (directive-dependent) to
    :meth:`read_value`.

    If it is not a directive, just ignore. That's how Hunspell works: .aff file can contain literally
    anything: pseudo-directives (lines looking like ``UPCASED_WORD some data`` but not a known directive
    name), free form text, etc. Even comments are implemented this way (and not by scanning for ``#``!)

    Args:
        source: passed from :meth:`read_aff` (because reading of one directive may require reading of
                more lines from source)
        line: current line read from source
        context: current reading context
    """

    name, *arguments = re.split(r'\s+', line)

    # Simplify a bit: no need to try reading value if the start doesn't even look like a directive...
    if not re.match(r'^[A-Z]+$', name):
        return None

    name = SYNONYMS.get(name, name)

    value = read_value(source, name, *arguments, context=context)

    if value is None:
        return None

    return (name, value)


def read_value(source: BaseReader, directive: str, *values, context: Context) -> Any:
    """
    Reads one value.

    Note that for a table-alike directives "one value" might span several lines (and that's why
    this method has ``source`` as its argument, and can read more lines from it on demand).

    For example, if current directive is ``BREAK``, it means the file below looks like this:

    .. code-block:: text

        BREAK 3     # we are on this line currently
        BREAK -
        BREAK ^-
        BREAK -$

    The method would read value 3, understand that there are 3 more lines to read, read them and
    return ``['-', '^-', '-$']``.

    The values read are immediately parsed into proper data types (see :mod:`data.aff <spylls.hunspell.data.aff>`
    for types definition).

    Args:
        source: Can be changed inside method
        directive: Name of current directive
        values: Values already read from the line where directive was
        context: Reading context
    """

    value = values[0] if values else None

    def _read_array(count=None):
        if not count:
            count = int(value)

        # TODO: handle if fetching it we'll find something NOT starting with teh expected directive name
        # TODO: \s+ => only space and tab, no unicode whitespaces
        return [
            re.split(r'\s+', ln)[1:]
            for num, ln in itertools.islice(source, count)
        ]

    if directive in ['SET', 'FLAG', 'KEY', 'TRY', 'WORDCHARS', 'LANG']:
        return value
    if directive == 'IGNORE':
        return aff.Ignore(value)
    if directive in ['MAXDIFF', 'MAXNGRAMSUGS', 'MAXCPDSUGS', 'COMPOUNDMIN', 'COMPOUNDWORDMAX']:
        return int(value)
    if directive in ['NOSUGGEST', 'KEEPCASE', 'CIRCUMFIX', 'NEEDAFFIX', 'FORBIDDENWORD', 'WARN',
                     'COMPOUNDFLAG', 'COMPOUNDBEGIN', 'COMPOUNDMIDDLE', 'COMPOUNDEND',
                     'ONLYINCOMPOUND',
                     'COMPOUNDPERMITFLAG', 'COMPOUNDFORBIDFLAG', 'FORCEUCASE',
                     'SUBSTANDARD',
                     'SYLLABLENUM', 'COMPOUNDROOT']:
        return context.parse_flag(value)
    if directive in ['COMPLEXPREFIXES', 'FULLSTRIP', 'NOSPLITSUGS', 'CHECKSHARPS',
                     'CHECKCOMPOUNDCASE', 'CHECKCOMPOUNDDUP', 'CHECKCOMPOUNDREP', 'CHECKCOMPOUNDTRIPLE',
                     'SIMPLIFIEDTRIPLE', 'ONLYMAXDIFF', 'COMPOUNDMORESUFFIXES']:
        # Presense of directive always means "turn it on"
        return True
    if directive == 'BREAK':
        return [aff.BreakPattern(first) for first, *_ in _read_array()]
    if directive == 'COMPOUNDRULE':
        return [aff.CompoundRule(first) for first, *_ in _read_array()]
    if directive in ['ICONV', 'OCONV']:
        return aff.ConvTable([
            (pat1, pat2) for pat1, pat2, *_rest in _read_array()    # pylint: disable=unnecessary-comprehension
        ])
    if directive == 'REP':
        return [aff.RepPattern(pat1, pat2) for pat1, pat2, *_rest in _read_array()]
    if directive in ['MAP']:
        return [
            [
                re.sub(r'[()]', '', s)
                for s in re.findall(r'(\([^()]+?\)|[^()])', chars)
            ]
            for chars, *_ in _read_array()
        ]
    if directive in ['SFX', 'PFX']:
        flag, crossproduct, count, *_ = values
        return [
            make_affix(directive, flag, crossproduct, *line, context=context)
            for line in _read_array(int(count))
        ]
    if directive == 'CHECKCOMPOUNDPATTERN':
        return [
            aff.CompoundPattern(left, right, rest[0] if rest else None)
            for left, right, *rest in _read_array()
        ]
    if directive == 'AF':
        return {
            str(i + 1): {*context.parse_flags(ln[0])}
            for i, ln in enumerate(_read_array())
        }
    if directive == 'AM':
        return {
            str(i + 1): {*ln}
            for i, ln in enumerate(_read_array())
        }
    if directive == 'COMPOUNDSYLLABLE':
        return (int(values[0]), values[1])
    if directive == 'PHONE':
        return aff.PhonetTable([
            (search, '' if replacement == '_' else replacement)
            for search, replacement, *_ in _read_array()
        ])

    # If it wasn't some known directive, it is not a data at all.
    return None


def make_affix(kind, flag, crossproduct, _, strip, add, *rest, context):
    """
    Produces Prefix/Suffix from raw data
    """

    kind_class = aff.Suffix if kind == 'SFX' else aff.Prefix

    # in LibreOffice ar.aff has at least one prefix (Ph) without any condition. Bug?
    cond = rest[0] if rest else ''
    add, _, flags = add.partition('/')
    if context.ignore:
        add = add.translate(context.ignore.tr)

    # TODO: Data fields (including AM)
    return kind_class(
        flag=flag,
        crossproduct=(crossproduct == 'Y'),
        strip=('' if strip == '0' else strip),
        add=('' if add == '0' else add),
        condition=cond,
        flags={*context.parse_flags(flags)}
    )
