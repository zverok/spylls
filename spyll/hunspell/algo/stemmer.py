import re
import itertools
import collections

Result = collections.namedtuple('Result', ['stem', 'prefix', 'suffix'], defaults=[None, None])

class Stemmer:
    def __init__(self, suffixes=[], prefixes=[]):
        self.suffixes = {
            flag: list(sufs) for flag, sufs in itertools.groupby(suffixes, key=lambda s: s.flag)
        }
        self.prefixes = {
            flag: list(prefs) for flag, prefs in itertools.groupby(prefixes, key=lambda s: s.flag)
        }

    # TODO: In fact, we should yield all the options, so the generator can be lazily consumed
    # and checked option-by-option through a dictionary
    def __call__(self, word):
        res = [Result(word)] # "Whole word" is always existing option
        for stem, suf in self.desuffix(word):
            res.append(Result(stem, suffix=suf))

        for stem, pref in self.deprefix(word):
            res.append(Result(stem, prefix=pref))
            if pref.crossproduct:
                for stem2, suf in self.desuffix(stem):
                    if suf.crossproduct:
                        res.append(Result(stem2, prefix=pref, suffix=suf))

        return res

    def desuffix(self, word):
        res = []
        # TODO: A suffix can have flag "I can have this additional suffixe(s) attached";
        # this should be checked, too.
        for flag, sufs in self.suffixes.items():
            for suf in sufs:
                if word.endswith(suf.add):
                    stem = word[0:-len(suf.add)] + suf.strip
                    if re.search(suf.condition + '$', stem):
                        res.append((stem, suf))
                        break # only one variant of a suffix should be found

        return res

    def deprefix(self, word):
        res = []
        for flag, prefs in self.prefixes.items():
            for pref in prefs:
                if word.startswith(pref.add):
                    stem = pref.strip + word[len(pref.add):]
                    if re.search('^' + pref.condition, stem):
                        res.append((stem, pref))
                        break # only one variant of a prefix should be found

        return res
