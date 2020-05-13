from enum import Enum

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

def apply(word: str, cap: Cap) -> str:
    if cap == Cap.NO:
        return word.lower()
    elif cap == Cap.INIT:
        return word.capitalize()
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
