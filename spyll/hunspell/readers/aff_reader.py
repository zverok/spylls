import re
import dataclasses
import typing as t

from spyll.hunspell.readers import FileReader, util
from spyll.hunspell.data import Aff
from spyll.hunspell.data import aff


class AffReader:
    FIELDS = {field.name: field for field in dataclasses.fields(Aff)}

    def __init__(self, path_or_io):
        self.source = FileReader(path_or_io)
        self.flag_format = 'short'

    def __call__(self):
        data = {}
        for (num, ln) in self.source:
            field, *parts = re.split(r'\s+', ln)

            # TODO: This is temp, to test on "real" dictionaries without understanding all
            # the fields. Maybe for ver. 0.0.1 it is acceptable, but should at least be
            # debug-logged.
            if field not in self.FIELDS:
                continue
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
            elif field == 'PSEUDOROOT':
                data['NEEDAFFIX'] = val
            else:
                data[field] = val

        return Aff(**data)

    # TODO: all Flag-typed directives should be read via util.parse_flags
    def _read_directive(self, field, *values):
        f = self.FIELDS[field]
        value = values[0] if values else None

        def _read_array(count = None):
            if not count:
                count = int(value)
            res = []
            # TODO: handle if there is not that number the <count> specified
            for i in range(int(count)):
                _, ln = self.source.__next__()
                _, *row = re.split(r'\s+', ln)
                res.append(row)
            return res

        if field in ['SET', 'FLAG', 'KEY', 'TRY']:
            return value
        elif field in ['MAXDIFF', 'MAXNGRAMSUGS', 'MAXCPDSUGS', 'COMPOUNDMIN', 'COMPOUNDWORDSMAX']:
            return int(value)
        elif field in ['NOSUGGEST', 'KEEPCASE', 'CIRCUMFIX', 'NEEDAFFIX', 'PSEUDOROOT', 'FORBIDDENWORD',
                       'COMPOUNDFLAG', 'COMPOUNDBEGIN', 'COMPOUNDMIDDLE', 'COMPOUNDLAST', 'ONLYINCOMPOUND',
                       'COMPOUNDPERMITFLAG', 'COMPOUNDFORBIDFLAG', 'FORCEUCASE']:
            return aff.Flag(value)
        elif field in ['CHECKCOMPOUNDCASE', 'CHECKCOMPOUNDDUP', 'CHECKCOMPOUNDREP', 'CHECKCOMPOUNDTRIPLE']:
            # Presense of directive always means "turn it on"
            return True
        elif field in ['BREAK', 'COMPOUNDRULE']:
            return [ln[0] for ln in _read_array()]
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
        else:
            # return tuple(values)
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
