import re
import itertools

class Stemmer:
    def __init__(self, suffixes=[], prefixes=[]):
        self.suffixes = {
            flag: list(sufs) for flag, sufs in itertools.groupby(suffixes, key=lambda s: s.flag)
        }
        self.prefixes = prefixes

    def desuffix(self, word):
        res = []
        for flag, sufs in self.suffixes.items():
            for suf in sufs:
                if word.endswith(suf.add):
                    stem = word[0:-len(suf.add)] + suf.strip
                    if re.search(suf.condition + '$', stem):
                        res.append((stem, suf))
                        break # only one variant of a suffix should be found

        return res
