import re
import itertools
from dataclasses import dataclass, field
from typing import Dict

from spyll.hunspell.readers import FileReader
from spyll.hunspell.data import Aff
from spyll.hunspell.data import aff


# Outdated directive names
SYNONYMS = {'PSEUDOROOT': 'NEEDAFFIX', 'COMPOUNDLAST': 'COMPOUNDEND'}


@dataclass
class FlagReader:
    format: str = 'short'
    synonyms: Dict[str, str] = field(default_factory=dict)

    def parse_one(self, string):
        return self.parse(string)[0]

    def parse(self, string):
        if string is None:
            return []

        if re.match(r'^\d+', string) and self.synonyms:
            return self.synonyms[string]

        # TODO: what if string format doesn't match expected (odd number of chars for long, etc.)?
        if self.format == 'short':
            return string
        elif self.format == 'long':
            return re.findall(r'..', string)
        elif self.format == 'num':
            return re.findall(r'\d+(?=,|$)', string)
        elif self.format == 'UTF-8':
            return string
        else:
            raise ValueError(f"Unknown flag format {self.format}")


def read_aff(path_or_io):
    source = FileReader(path_or_io)
    data = {'SFX': {}, 'PFX': {}, 'FLAG': 'short'}
    flag_reader = FlagReader(format='short')

    for (num, line) in source:
        directive, value = read_directive(source, line, flag_reader=flag_reader)

        if not directive:
            continue

        if directive in ['SFX', 'PFX']:
            data[directive][value[0].flag] = value
        else:
            data[directive] = value

        # Additional actions, changing further reading behavior
        if directive == 'FLAG':
            flag_reader = FlagReader(format=value)
        elif directive == 'AF':
            flag_reader = FlagReader(format=flag_reader.format, synonyms=value)
        elif directive == 'SET':
            source.reset_encoding(value)

        if directive == 'FLAG' and value == 'UTF-8':
            data['SET'] = 'UTF-8'
            source.reset_encoding('UTF-8')

    return (Aff(**data), flag_reader)


def read_directive(source, line, *, flag_reader):
    name, *arguments = re.split(r'\s+', line)

    # base_utf has lines like McDonalds’sá/w -- at the end...
    # TODO: Check what's hunspell's logic to deal with this
    if not re.match(r'^[A-Z]+$', name):
        return (None, None)

    name = SYNONYMS.get(name, name)

    value = read_value(source, name, *arguments, flag_reader=flag_reader)

    return (name, value)


# TODO: all Flag-typed directives should be read via util.parse_flags
def read_value(source, directive, *values, flag_reader):
    value = values[0] if values else None

    def _read_array(count=None):
        if not count:
            count = int(value)

        # TODO: handle if fetching it we'll find something NOT starting with teh expected directive name
        return [
            re.split(r'\s+', ln)[1:]
            for num, ln in itertools.islice(source, count)
        ]

    if directive in ['SET', 'FLAG', 'KEY', 'TRY', 'WORDCHARS', 'IGNORE', 'LANG']:
        return value
    elif directive in ['MAXDIFF', 'MAXNGRAMSUGS', 'MAXCPDSUGS', 'COMPOUNDMIN', 'COMPOUNDWORDMAX']:
        return int(value)
    elif directive in ['NOSUGGEST', 'KEEPCASE', 'CIRCUMFIX', 'NEEDAFFIX', 'FORBIDDENWORD', 'WARN',
                       'COMPOUNDFLAG', 'COMPOUNDBEGIN', 'COMPOUNDMIDDLE', 'COMPOUNDEND',
                       'ONLYINCOMPOUND',
                       'COMPOUNDPERMITFLAG', 'COMPOUNDFORBIDFLAG', 'FORCEUCASE']:
        return aff.Flag(flag_reader.parse_one(value))
    elif directive in ['COMPLEXPREFIXES', 'FULLSTRIP', 'NOSPLITSUGS', 'CHECKSHARPS',
                       'CHECKCOMPOUNDCASE', 'CHECKCOMPOUNDDUP', 'CHECKCOMPOUNDREP', 'CHECKCOMPOUNDTRIPLE',
                       'SIMPLIFIEDTRIPLE']:
        # Presense of directive always means "turn it on"
        return True
    elif directive in ['BREAK', 'COMPOUNDRULE']:
        return [first for first, *_ in _read_array()]
    elif directive in ['REP', 'ICONV', 'OCONV']:
        return [tuple(ln) for ln in _read_array()]
    elif directive in ['MAP']:
        return [
            [
                re.sub(r'[()]', '', s)
                for s in re.findall(r'(\([^()]+?\)|[^()])', ln[0])
            ]
            for ln in _read_array()
        ]
    elif directive in ['SFX', 'PFX']:
        flag, crossproduct, count = values
        return [
            make_affix(directive, flag, crossproduct, *line, flag_reader=flag_reader)
            for line in _read_array(int(count))
        ]
    elif directive == 'CHECKCOMPOUNDPATTERN':
        return [
            (left, right, rest[0] if rest else None)
            for left, right, *rest in _read_array()
        ]
    elif directive == 'AF':
        return {
            str(i + 1): {*flag_reader.parse(ln[0])}
            for i, ln in enumerate(_read_array())
        }
    elif directive == 'AM':
        return {
            str(i + 1): {*ln}
            for i, ln in enumerate(_read_array())
        }
    elif directive == 'COMPOUNDSYLLABLE':
        return (int(values[0]), values[1])
    else:
        # TODO: Maybe for ver 0.0.1 it is acceptable to just not recognize some flags?
        raise Exception(f"Can't parse {directive}")


def make_affix(kind, flag, crossproduct, _, strip, add, *rest, flag_reader):
    kind_class = aff.Suffix if kind == 'SFX' else aff.Prefix

    # in LibreOffice ar.aff has at least one prefix (Ph) without any condition. Bug?
    cond = rest[0] if rest else ''
    add, _, flags = add.partition('/')
    return kind_class(
        flag=flag,
        crossproduct=(crossproduct == 'Y'),
        strip=('' if strip == '0' else strip),
        add=('' if add == '0' else add),
        condition=cond,
        flags={*flag_reader.parse(flags)}
    )
