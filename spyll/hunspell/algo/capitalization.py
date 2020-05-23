from enum import Enum
from typing import Tuple, List

Cap = Enum('Cap', 'NO INIT ALL HUHINIT HUH')


def guess(word: str) -> Cap:
    if word.lower() == word:
        return Cap.NO
    elif word[:1].lower() + word[1:] == word.lower():
        return Cap.INIT
    elif word.upper() == word:
        return Cap.ALL
    elif word[:1].lower() != word[:1]:
        return Cap.HUHINIT
    else:
        return Cap.HUH


def coerce(word: str, cap: Cap) -> str:
    if cap == Cap.INIT or cap == Cap.HUHINIT:
        return upperfirst(word)
    elif cap == Cap.ALL:
        return word.upper()
    else:
        return word


def lowerfirst(word: str) -> str:
    return word[0].lower() + word[1:]


def upperfirst(word: str) -> str:
    return word[0].upper() + word[1:]

def lower(word: str) -> str:
    # turkic "lowercase dot i" to latinic "i"
    return word.lower().replace('i̇', 'i')

def capitalize(word: str) -> str:
    was_dot_i = word[0] == 'İ'
    res = lower(word).capitalize()
    return 'İ' + res[1:] if was_dot_i else res

def variants(word: str, *, lang_with_dot_i=False) -> Tuple[Cap, List[str]]:
    captype = guess(word)

    was_dot_i = word and word[0] == 'İ'
    allow_lower = not was_dot_i or lang_with_dot_i

    if captype == Cap.NO:
        return (captype, [word])
    elif captype == Cap.INIT:
        if allow_lower:
            return (captype, [word, lower(word)])
        else:
            return (captype, [word])
    elif captype == Cap.HUHINIT:
        if allow_lower:
            return (captype, [word, lowerfirst(word), lower(word), capitalize(word)])
        else:
            return (captype, [word, capitalize(word)])
        # TODO: also here and below, consider the theory FooBar meant Foo Bar
    elif captype == Cap.HUH:
        return (captype, [word, lower(word)])
    elif captype == Cap.ALL:
        if allow_lower:
            return (captype, [word, lower(word), capitalize(word)])
        else:
            return (captype, [word, capitalize(word)])
