import re
import itertools
import collections

from spyll.hunspell.algo import compounder as cpd

Result = collections.namedtuple('Result',
    ['stem', 'prefix', 'suffix', 'prefix2', 'suffix2'],
    defaults=[None, None, None, None]
)

def only_affix_need_affix(form, flag):
    all_affixes = list(filter(None, [form.prefix, form.prefix2, form.suffix, form.suffix2]))
    if not all_affixes:
        return False
    needaffs = [aff for aff in all_affixes if flag in aff.flags]
    return len(all_affixes) == len(needaffs)

class Stemmer:
    def __init__(self, suffixes=[], prefixes=[], needaffix=None, compoundpermit=None, compoundforbid=None):
        self.suffixes = {
            flag: list(sufs) for flag, sufs in itertools.groupby(suffixes, key=lambda s: s.flag)
        }
        self.prefixes = {
            flag: list(prefs) for flag, prefs in itertools.groupby(prefixes, key=lambda s: s.flag)
        }
        self.needaffix = needaffix
        self.compoundpermit = compoundpermit
        self.compoundforbid = compoundforbid

    # TODO: In fact, we should yield all the options, so the generator can be lazily consumed
    # and checked option-by-option through a dictionary
    def __call__(self, word, compoundpos=None):
        res = [Result(word)] # "Whole word" is always existing option

        for form in self.desuffix(word, compoundpos=compoundpos):
            res.append(form)

        for form in self.deprefix(word, compoundpos=compoundpos):
            res.append(form)
            if form.prefix.crossproduct:
                for form2 in self.desuffix(form.stem, compoundpos=compoundpos):
                    if form2.suffix.crossproduct:
                        res.append(form2._replace(prefix=form.prefix))

        if self.needaffix:
            res = [r for r in res if not only_affix_need_affix(r, self.needaffix)]

        return res

    def desuffix(self, word, extra_flag=None, compoundpos=None):
        res = []
        for stem, suf in self._desuffix(word, extra_flag=extra_flag, compoundpos=compoundpos):
            res.append(Result(stem, suffix=suf))
            if not extra_flag: # only one level depth
                for form2 in self.desuffix(stem, extra_flag=suf.flag, compoundpos=compoundpos):
                    res.append(form2._replace(suffix2=suf))
        return res

    def deprefix(self, word, extra_flag=None, compoundpos=None):
        res = []
        for stem, pref in self._deprefix(word, extra_flag=extra_flag, compoundpos=compoundpos):
            res.append(Result(stem, prefix=pref))
            if not extra_flag: # only one level depth
                for form2 in self.deprefix(stem, extra_flag=pref.flag, compoundpos=compoundpos):
                    res.append(form2._replace(prefix2=pref))
        return res

    def _desuffix(self, word, extra_flag=None, compoundpos=None):
        if compoundpos is None or compoundpos == cpd.Pos.END:
            checkpermit = False
        else:
            # No possibility any suffix will be OK
            if not self.compoundpermit: return []
            checkpermit = True

        res = []
        for flag, sufs in self.suffixes.items():
            for suf in sufs:
                if extra_flag and not extra_flag in suf.flags: continue
                if checkpermit and not self.compoundpermit in suf.flags: continue
                if compoundpos is not None and self.compoundforbid in suf.flags: continue

                if word.endswith(suf.add) or suf.add == '':
                    if suf.add == '':
                        stem = word + suf.strip
                    else:
                        stem = word[0:-len(suf.add)] + suf.strip
                    if re.search(suf.condition + '$', stem):
                        res.append((stem, suf))
                        # TODO: seems that only one variant of a suffix should be found?
                        # but not the FIRST POSSIBLE one -- otherwise, say, base/implied test breaks.

        return res

    def _deprefix(self, word, extra_flag=None, compoundpos=None):
        if compoundpos is None or compoundpos == cpd.Pos.BEGIN:
            checkpermit = False
        else:
            # No possibility any prefix will be OK
            if not self.compoundpermit: return []
            checkpermit = True

        res = []
        for flag, prefs in self.prefixes.items():
            for pref in prefs:
                if extra_flag and not extra_flag in pref.flags: continue
                if checkpermit and not self.compoundpermit in pref.flags: continue
                if compoundpos is not None and self.compoundforbid in pref.flags: continue

                if word.startswith(pref.add) or pref.add == '':
                    stem = pref.strip + word[len(pref.add):]
                    if re.search('^' + pref.condition, stem):
                        res.append((stem, pref))
                        # TODO: seems that only one variant of a prefix should be found?

        return res
