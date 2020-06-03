import re
import itertools

from spyll.hunspell.readers import FileReader, util
from spyll.hunspell.data import Aff
from spyll.hunspell.data import aff


class AffReader:
    SYNONYMS = {'PSEUDOROOT': 'NEEDAFFIX', 'COMPOUNDLAST': 'COMPOUNDEND'}

    def __init__(self, path_or_io):
        self.source = FileReader(path_or_io)
        self.flag_format = 'short'

    def __call__(self):
        data = {}
        for (num, ln) in self.source:
            field, *parts = re.split(r'\s+', ln)

            # base_utf has lines like McDonalds’sá/w -- at the end...
            # TODO: Check what's hunspell's logic to deal with this
            if not re.match(r'^[A-Z]+$', field):
                continue

            field = self.SYNONYMS.get(field, field)
            val = self._read_directive(field, *parts)
            if field == 'FLAGS':
                self.flag_format = val
            elif field == 'SET':
                self.source.reset_encoding(val)
                data[field] = val
            elif field in ['SFX', 'PFX']:
                if field not in data:
                    data[field] = {}
                data[field][val[0].flag] = val
            else:
                data[field] = val

        return Aff(**data)

    # TODO: all Flag-typed directives should be read via util.parse_flags
    def _read_directive(self, field, *values):
        value = values[0] if values else None

        def _read_array(count=None):
            if not count:
                count = int(value)

            # TODO: handle if fetching it we'll find something NOT starting with teh expected field name
            return [
                re.split(r'\s+', ln)[1:]
                for num, ln in itertools.islice(self.source, count)
            ]

        if field in ['SET', 'FLAG', 'KEY', 'TRY', 'WORDCHARS', 'IGNORE', 'LANG']:
            return value
        elif field in ['MAXDIFF', 'MAXNGRAMSUGS', 'MAXCPDSUGS', 'COMPOUNDMIN', 'COMPOUNDWORDMAX']:
            return int(value)
        elif field in ['NOSUGGEST', 'KEEPCASE', 'CIRCUMFIX', 'NEEDAFFIX', 'FORBIDDENWORD', 'WARN',
                       'COMPOUNDFLAG', 'COMPOUNDBEGIN', 'COMPOUNDMIDDLE', 'COMPOUNDEND',
                       'ONLYINCOMPOUND',
                       'COMPOUNDPERMITFLAG', 'COMPOUNDFORBIDFLAG', 'FORCEUCASE']:
            return aff.Flag(value)
        elif field in ['COMPLEXPREFIXES', 'FULLSTRIP', 'NOSPLITSUGS', 'CHECKSHARPS',
                       'CHECKCOMPOUNDCASE', 'CHECKCOMPOUNDDUP', 'CHECKCOMPOUNDREP', 'CHECKCOMPOUNDTRIPLE',
                       'SIMPLIFIEDTRIPLE']:
            # Presense of directive always means "turn it on"
            return True
        elif field in ['BREAK', 'COMPOUNDRULE']:
            return [first for first, *_ in _read_array()]
        elif field in ['REP', 'ICONV', 'OCONV']:
            return [tuple(ln) for ln in _read_array()]
        elif field in ['MAP']:
            return [
                [
                    re.sub(r'[()]', '', s)
                    for s in re.findall(r'(\([^()]+?\)|[^()])', ln[0])
                ]
                for ln in _read_array()
            ]
        elif field in ['SFX', 'PFX']:
            flag, crossproduct, count = values
            return [
                self.make_affix(field, flag, crossproduct, *line)
                for line in _read_array(int(count))
            ]
        elif field == 'CHECKCOMPOUNDPATTERN':
            return [
                (left, right, rest[0] if rest else None)
                for left, right, *rest in _read_array()
            ]
        elif field == 'AF':
            return [
                (i + 1, util.parse_flags(ln[0], format=self.flag_format))
                for i, ln in enumerate(_read_array())
            ]
        elif field == 'COMPOUNDSYLLABLE':
            return (int(values[0]), values[1])
        else:
            # TODO: Maybe for ver 0.0.1 it is acceptable to just not recognize some flags?
            raise Exception(f"Can't parse {field}")

    def make_affix(self, kind, flag, crossproduct, _, strip, add, *rest):
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
            flags=set(flags)
        )
