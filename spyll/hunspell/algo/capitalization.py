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
    # if cap == Cap.NO:
    #     return word.lower()
    if cap == Cap.INIT or cap == Cap.HUHINIT:
        return upperfirst(word)
    elif cap == Cap.ALL:
        return word.upper()
    else:
        return word

def for_suggestion(suggestion: str, cap: Cap) -> str:
    if (cap == Cap.INIT or cap == Cap.ALL) and guess(suggestion) == Cap.NO:
        return apply(suggestion, cap)
    else:
        return suggestion

def lowerfirst(word: str) -> str:
    return word[0].lower() + word[1:]

def upperfirst(word: str) -> str:
    return word[0].upper() + word[1:]

def variants(word: str) -> Tuple[Cap, List[str]]:
    captype = guess(word)

    if captype == Cap.NO:
        return (captype, [word])
    elif captype == Cap.INIT:
        return (captype, [word, word.lower()])
    elif captype == Cap.HUHINIT:
        return (captype, [word, lowerfirst(word), word.lower(), word.lower().capitalize()])
        # TODO: also here and below, consider the theory FooBar meant Foo Bar
    elif captype == Cap.HUH:
        return (captype, [word, word.lower()])
    elif captype == Cap.ALL:
        return (captype, [word, word.lower(), word.lower().capitalize()])
