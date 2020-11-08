from enum import Enum
from typing import Tuple, List, Iterator

Type = Enum('Type', 'NO INIT ALL HUHINIT HUH')


class Collation:
    def guess(self, word: str, *, for_corrections=False) -> Type:   # pylint: disable=unused-argument,no-self-use
        if word.lower() == word:
            return Type.NO
        if word[:1].lower() + word[1:] == word.lower():
            return Type.INIT
        if word.upper() == word:
            return Type.ALL
        if word[:1].lower() != word[:1]:
            return Type.HUHINIT
        return Type.HUH

    def lower(self, word) -> List[str]:  # pylint: disable=no-self-use
        # can't be properly lowercased in non-Turkic collaction
        if word[0] == 'İ':
            return []

        # turkic "lowercase dot i" to latinic "i", just in case
        return [word.lower().replace('i̇', 'i')]

    def upper(self, word) -> str:   # pylint: disable=no-self-use
        return word.upper()

    def capitalize(self, word) -> Iterator[str]:
        return (self.upper(word[0]) + lower for lower in self.lower(word[1:]))

    def lowerfirst(self, word) -> Iterator[str]:
        return (letter + word[1:] for letter in self.lower(word[0]))

    def variants(self, word: str) -> Tuple[Type, List[str]]:
        captype = self.guess(word)

        if captype == Type.NO:
            result = [word]
        elif captype == Type.INIT:
            result = [word, *self.lower(word)]
        elif captype == Type.HUHINIT:
            result = [word, *self.lowerfirst(word)]
            # TODO: also here and below, consider the theory FooBar meant Foo Bar
        elif captype == Type.HUH:
            result = [word]
        elif captype == Type.ALL:
            result = [word, *self.lower(word), *self.capitalize(word)]

        return (captype, result)

    def corrections(self, word: str) -> Tuple[Type, List[str]]:
        captype = self.guess(word, for_corrections=True)

        if captype == Type.NO:
            result = [word] # FIXME: Add capitalized form?..
        elif captype == Type.INIT:
            result = [word, *self.lower(word)]
        elif captype == Type.HUHINIT:
            result = [word, *self.lowerfirst(word), *self.lower(word), *self.capitalize(word)]
            # TODO: also here and below, consider the theory FooBar meant Foo Bar
        elif captype == Type.HUH:
            result = [word, *self.lower(word)]
        elif captype == Type.ALL:
            result = [word, *self.lower(word), *self.capitalize(word)]

        return (captype, result)

    def coerce(self, word: str, cap: Type) -> str:
        if cap in (Type.INIT, Type.HUHINIT):
            return self.upper(word[0]) + word[1:]
        if cap == Type.ALL:
            return self.upper(word)
        return word


class TurkicCollation(Collation):
    U2L = str.maketrans('İI', 'iı')
    L2U = str.maketrans('iı', 'İI')

    def lower(self, word):
        return super().lower(word.translate(self.U2L))

    def upper(self, word):
        return super().upper(word.translate(self.L2U))


class GermanCollation(Collation):
    def lower(self, word):
        def sharp_s_variants(text, start=0):
            pos = text.find('ss', start)
            if pos == -1:
                return []
            replaced = text[:pos] + 'ß' + text[pos+2:]
            return [replaced, *sharp_s_variants(replaced, pos+1), *sharp_s_variants(text, pos+2)]

        lowered = super().lower(word)[0]

        if 'SS' in word:
            return [*sharp_s_variants(lowered), lowered]

        return [lowered]

    def guess(self, word, *, for_corrections=False):
        result = super().guess(word)
        if for_corrections and 'ß' in word and super().guess(word.replace('ß', '')) == Type.ALL:
            return Type.ALL
        return result
