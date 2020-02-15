from spyll.hunspell.readers import AffReader, DicReader
from spyll.hunspell.algo import Stemmer

class Dictionary:
    def __init__(self, path):
        self.aff = AffReader(path + '.aff')()
        self.dic = DicReader(path + '.dic', encoding = self.aff.set, flag_format = self.aff.flag)()
        self.stemmer = Stemmer(prefixes = self.aff.pfx, suffixes = self.aff.sfx)

    def lookup(self, word):
        forms = self.stemmer(word)
        res = []
        for form in forms:
            for w in self.dic.words:
                if w.stem == form.stem and self._is_compatible(w, form):
                    res.append(form)

        return res

    def _is_compatible(self, dic_word, stem_form):
        if stem_form.suffix and stem_form.suffix.flag not in dic_word.flags:
            return False
        if stem_form.prefix and stem_form.prefix.flag not in dic_word.flags:
            return False
        # TODO: no suffix/prefix, and the word has needsaffix flag, return false
        return True
