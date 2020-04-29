import itertools
from typing import List, Iterator, Union, Optional, Any, Tuple

from spyll.hunspell import data
from spyll.hunspell.algo import lookup
from spyll.hunspell.algo import permutations as pmt

def suggest(aff: data.Aff, dic: data.Dic, word: str) -> Iterator[str]:
    seen = set()
    for sug in list_suggestions(aff, word):
        if not sug in seen and lookup.lookup(aff, dic, sug):
            yield sug
            seen.add(sug)

def list_suggestions(aff: data.Aff, word: str) -> Iterator[str]:
    return itertools.chain(
        [word.upper()],  # suggestions for an uppercase word (html -> HTML)
        pmt.replchars(word, aff.rep),    # perhaps we made a typical fault of spelling
        pmt.mapchars(word, aff.map),    # perhaps we made chose the wrong char from a related set
        pmt.swapchar(word), # did we swap the order of chars by mistake
        pmt.longswapchar(word), # did we swap the order of non adjacent chars by mistake
        pmt.badcharkey(word, aff.key), # did we just hit the wrong key in place of a good char (case and keyboard)
        pmt.extrachar(word), # did we add a char that should not be there
        pmt.forgotchar(word, aff.try_), # did we forgot a char
        pmt.movechar(word), # did we move a char
        pmt.badchar(word, aff.try_), # did we just hit the wrong key in place of a good char
        pmt.doubletwochars(word), # did we double two characters

        # # perhaps we forgot to hit space and two words ran together
        # # (dictionary word pairs have top priority here, so
        # # we always suggest them, in despite of nosplitsugs, and
        # # drop compound word and other suggestions)
        # pmt.twowords(word, use_dash='-' in aff.try_ or 'a' in aff.try_)
    )


# def suggest(aff: data.Aff, dic: data.Dic, word: str) -> Iterator[str]:
#     # TODO:
#     # * filter bad capitalization and forbidden words
#     # * remove duplicates
#     # * appy oconv
#     for sug in suggest_internal(str):
#         yield sug

# def suggest_internal(aff: data.Aff, dic: data.Dic, word: str) -> Iterator[str]:
#     # TODO: apply iconv

#     # TODO: cleanword2 & guess capitalization

#     captype = guess_capitalization(word)

#     if aff.forceucase and captype == Cap.NO:
#         uword = word.upper()
#         if lookup.lookup(aff, dic, uword):
#             yield uword
#             return

#     if captype == Cap.NO:
#         for sug in mgr_suggest(word):
#             yield sug
#         # TODO: if capitalization found it is abbreviation (with dots?..) do something about it!
#         # TODO: control clock and return if necessary
#     elif captype == Cap.INIT:
#         for sug in mgr_suggest(word):
#             yield sug

#         # FIXME: Hunspell tries to suggest from downcased only if original case not found...
#         for sug in mgr_suggest(word.downcase()):
#             yield sug

#     elif cap == HUH or cap == HUHINIT:
#         # TODO!
#         pass
#     elif cap == ALL:
#         # TODO!
#         pass

#     # TODO: special LANG_hu section: replace '-' with ' ' in Hungarian

#     # TODO: ngram-based ("very bad") suggestions

#     # TODO: try dash suggestion (Afo-American -> Afro-American)

# def mgr_suggset(aff: data.Aff, dic: data.Dic, word: str) -> Iterator[str]:
#     # TODO: clock support should be implemented by caller:
#     #   for sug in mrg_suggest:
#     #      if TIME_IS_UP: break
#     #      yield sug


#     # first try without cpdsuggest, then with it
#     # cpdsuggest is passed to "check if it is existing word": on the first pass we don't try
#     # to check the compounding, because it is slooower
#     for cpdsugges in [False, True]:
#         # everywhere below we check cpdsuggest == 0 (not a compounding) or not too many

#         # suggestions for an uppercase word (html -> HTML)
#         yield word.upper()
#         # perhaps we made a typical fault of spelling
#         replchars(word, aff.rep)
#         # perhaps we made chose the wrong char from a related set
#         mapchars(word, aff.map)
#         # did we swap the order of chars by mistake
#         swapchar(word)
#         # did we swap the order of non adjacent chars by mistake
#         longswapchar(word)
#         # did we just hit the wrong key in place of a good char (case and keyboard)
#         badcharkey(word, aff.key)
#         # did we add a char that should not be there
#         extrachar(word)
#         # did we forgot a char
#         forgotchar(word, aff.try_)
#         # did we move a char
#         movechar(word)
#         # did we just hit the wrong key in place of a good char
#         badchar(word)
#         # did we double two characters
#         doubletwochars(word)

#         # perhaps we forgot to hit space and two words ran together
#         # (dictionary word pairs have top priority here, so
#         # we always suggest them, in despite of nosplitsugs, and
#         # drop compound word and other suggestions)
#         twowords(word, use_dash='-' in aff.try_ or 'a' in aff.try_)


#     # in the end, we should report:
#     # * what we found
#     # * is there a "good" suggestion
#     # * if all suggestions are compound ones

# # def mrg_nsuggest(aff: data.Aff, dic: data.Dic, word: str) -> Iterator<str>:
