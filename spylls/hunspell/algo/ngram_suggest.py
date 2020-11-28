"""
.. autofunction:: ngram_suggest

.. autofunction:: forms_for
.. autofunction:: filter_guesses

Scoring
^^^^^^^

.. autofunction:: detect_threshold
.. autofunction:: root_score
.. autofunction:: rough_affix_score
.. autofunction:: precise_affix_score

"""

from typing import Iterator, Tuple, List, Set, Dict
from operator import itemgetter
import heapq

from spylls.hunspell import data
import spylls.hunspell.algo.string_metrics as sm


MAX_ROOTS = 100
MAX_GUESSES = 200


def ngram_suggest(misspelling: str, *,
                  dictionary_words: List[data.dic.Word],
                  prefixes: Dict[str, List[data.aff.Prefix]],
                  suffixes: Dict[str, List[data.aff.Suffix]],
                  known: Set[str], maxdiff: int, onlymaxdiff: bool = False) -> Iterator[str]:
    """
    Try to suggest all possible variants for misspelling based on ngram-similarity.

    Internally:

    * calculates misspelling similarity to all dictionary word stems with :meth:`root_score`, and
      choses the best ones
    * of those words, produces all forms possible with suffixes/prefixes by :meth:`forms_for`,
      calculates their score against misspelling with :meth:`rough_affix_score` and choses the best ones,
      using threshold calculated in :meth:`detect_threshold`
    * calculates more precise (but more time-consuming) score for those with :meth:`precise_affix_score` and
      sorts by it
    * filters suggestions depending on their score with :meth:`filter_guesses`

    Args:
        misspelling: Misspelled word
        dictionary_words: all entries from dictionary to iterate agains (without forbidden, ``ONLYINCOMPOUND``
                          and such)
        prefixes: all prefixes from .aff file to try produce forms with
        suffixes: all suffixes from .aff file to try produce forms with
        maxdiff: contents of :attr:`Aff.MAXDIFF <spylls.hunspell.data.aff.Aff.MAXDIFF>` (changes amount of suggestions)
        onlymaxdiff: contents of :attr:`Aff.ONLYMAXDIFF <spylls.hunspell.data.aff.Aff.ONLYMAXDIFF>`
                     (exlcudes not very good suggestions, see :meth:`filter_guesses`)
    """

    root_scores: List[Tuple[float, str, data.dic.Word]] = []

    # First, find MAX_ROOTS candidate dictionary entries, by calculating stem score against the
    # misspelled word.
    for word in dictionary_words:
        if abs(len(word.stem) - len(misspelling)) > 4:
            continue

        # TODO: hunspell has more exceptions/flag checks here (part of it we cover later in suggest,
        # deciding, for example, if the suggestion is forbidden)

        score = root_score(misspelling, word.stem)

        # If dictionary word have alternative spellings provided via `pp:` data tag, calculate
        # score against them, too. Note that only simple ph:spelling are listed in alt_spellings,
        # more complicated tags like ph:spellin* or ph:spellng->spelling are ignored in ngrams
        if word.alt_spellings:
            for variant in word.alt_spellings:
                score = max(score, root_score(misspelling, variant))

        # Pythons stdlib heapq used to always keep only MAX_ROOTS of best results
        if len(root_scores) > MAX_ROOTS:
            heapq.heappushpop(root_scores, (score, word.stem, word))
        else:
            heapq.heappush(root_scores, (score, word.stem, word))

    roots = heapq.nlargest(MAX_ROOTS, root_scores)

    # "Minimum passable" suggestion threshold (decided by replacing some chars in word with * and
    # calculating what score it would have).
    threshold = detect_threshold(misspelling)

    guess_scores: List[Tuple[float, str, str]] = []

    # Now, for all "good" dictionary words, generate all of their forms with suffixes/prefixes, and
    # calculate their scores.
    # Produced structure is (score, word_variant_to_calculate_score, word_form_to_suggest)
    # The second item is, again, to support alternative spellings suggested in dictionary by ``ph:``
    # tag.
    for (_, _, root) in roots:
        if root.alt_spellings:
            # If any of alternative spelling passes the threshold
            for variant in root.alt_spellings:
                score = rough_affix_score(misspelling, variant)
                if score > threshold:
                    # ...we add them to the final suggestion list (but don't try to produce affix forms)
                    heapq.heappush(guess_scores, (score, variant, root.stem))

        # For all acceptable forms from current dictionary word (with all possible suffixes and prefixes)...
        for form in forms_for(root, prefixes, suffixes, similar_to=misspelling):
            score = rough_affix_score(misspelling, form.lower())
            if score > threshold:
                # ...push them to final suggestion list if they pass the threshold
                heapq.heappush(guess_scores, (score, form, form))

    # We are done generating guesses. Take only limited amount, and sort in order of decreasing score.
    guesses = heapq.nlargest(MAX_GUESSES, guess_scores)

    fact = (10.0 - maxdiff) / 5.0 if maxdiff >= 0 else 1.0

    # Now, calculate more precise scores for all good suggestions
    guesses2 = [
        (precise_affix_score(misspelling, compared.lower(), fact, base=score), real)
        for (score, compared, real) in guesses
    ]

    # ...and sort them based on that score.
    # (NB: actually, we might not need ``key`` here, but it is
    # added for sorting stability; doesn't changes the objective quality of suggestions, but passes
    # hunspell test ``phone.sug``!)
    guesses2 = sorted(guesses2, key=itemgetter(0), reverse=True)

    # We can return suggestions now (but filter them to not overflow with)
    yield from filter_guesses(guesses2, known=known, onlymaxdiff=onlymaxdiff)

# Scoring algorithms
# ------------------


def root_score(word1: str, word2: str) -> float:
    """
    Scoring, stage 1: Simple score for first dictionary words chosing: 3-gram score + longest start
    substring.

    Args:
        word1: misspelled word
        word2: possible suggestion
    """

    return (
        sm.ngram(3, word1, word2.lower(), longer_worse=True) +
        sm.leftcommonsubstring(word1, word2.lower())
    )


def rough_affix_score(word1: str, word2: str) -> float:
    """
    Scoring, stage 2: First (rough and quick) score of affixed forms: n-gram score with n=length of
    the misspelled word + longest start substring

    Args:
        word1: misspelled word
        word2: possible suggestion
    """

    return (
        sm.ngram(len(word1), word1, word2, any_mismatch=True) +
        sm.leftcommonsubstring(word1, word2)
    )


def precise_affix_score(word1: str, word2: str, diff_factor: float, *, base: float) -> float:
    """
    Scoring, stage 3: Hardcore final score for affixed forms!

    It actually produces score of one of 3 groups:

    * > 1000: if the words are actually same with different casing (shouldn't happen when called from
      suggest, it should've already handled that!)
    * < -100: if the word difference is too much (what is "too much" defined by ``diff_factor``), only
      one of those questionable suggestions would be returned
    * -100...1000: just a normal suggestion score, defining its sorting position

    See also :meth:`filter_guesses` below which uses this separation into "groups" to drop some results.

    Args:
        word1: misspelled word
        word2: possible suggestion
        diff_factor: factor changing amount of suggestions (:attr:`Aff.MAXDIFF <spylls.hunspell.data.aff.Aff.MAXDIFF>`)
        base: initial score of word1 against word2
    """

    lcs = sm.lcslen(word1, word2)

    # same characters with different casing -- "very good" suggestion class
    if len(word1) == len(word2) and len(word1) == lcs:
        return base + 2000

    # Score is: length of longest common subsequent minus length difference...
    result = 2 * lcs - abs(len(word1) - len(word2))

    # increase score by length of common start substring
    result += sm.leftcommonsubstring(word1, word2)

    cps, is_swap = sm.commoncharacterpositions(word1, word2.lower())
    # Add 1 if there were _any_ occurence of "same chars in same positions" in two words
    if cps:
        result += 1
    # Add 10 if the only difference of two words is "exactly two characters swapped"
    if is_swap:
        result += 10

    # Add regular four-gram weight
    result += sm.ngram(4, word1, word2, any_mismatch=True)

    # Sum of weighted bigrams used to estimate result quality
    bigrams = (
        sm.ngram(2, word1, word2, any_mismatch=True, weighted=True) +
        sm.ngram(2, word2, word1, any_mismatch=True, weighted=True)
    )

    result += bigrams

    # diff_factor's ranges from 0 to 2 (depending of aff.MAXDIFF=0..10, with 10 meaning "give me all
    # possible ngrams" and 0 meaninig "avoid most of the questionable ngrams"); with MAXDIFF=10 the
    # factor would be 0, and this branch will be avoided; with MAXDIFF=0 the factor would be 2, and
    # lots of "slihtly similar" words would be dropped into "questionable" bag.
    if bigrams < (len(word1) + len(word2)) * diff_factor:
        result -= 1000

    return result


def detect_threshold(word: str) -> float:
    """
    Find minimum threshold for a passable suggestion

    Mangle original word three differnt ways (by replacing each 4th character with "*", starting from
    1st, 2nd or 3rd), and score them to generate a minimum acceptable score.

    Args:
        word: misspelled word
    """

    thresh = 0.0

    for start_pos in range(1, 4):
        mangled = list(word)
        for pos in range(start_pos, len(word), 4):
            mangled[pos] = '*'

        mangled_word = ''.join(mangled)

        thresh += sm.ngram(len(word), word, mangled_word, any_mismatch=True)

    # Take average of the three scores
    return thresh // 3 - 1


def forms_for(word: data.dic.Word, all_prefixes, all_suffixes, *, similar_to: str):
    """
    Produce forms with all possible affixes and prefixes from the dictionary word, but only those
    the ``candidate`` can have. Note that there is no comprehensive flag checks (like "this prefix
    is prohibited with suffix with this flag"). Probably main suggest's code should check it
    (e.g. use ``filter_guesses`` (in
    :meth:`suggest_internal <spylls.hunspell.algo.suggest.Suggest.suggest_internal>`)
    for ngram-based suggestions, too).

    Args:
        word: dictionary stem to produce forms for
        all_prefixes:
        all_suffixes:
        similar_to: initial misspelling (to filter suffixes/prefixes against it)
    """

    # word without prefixes/suffixes is also present
    res = [word.stem]

    suffixes = [
        suffix
        for flag in word.flags
        for suffix in all_suffixes.get(flag, [])
        if suffix.cond_regexp.search(word.stem) and similar_to.endswith(suffix.add)
    ]
    prefixes = [
        prefix
        for flag in word.flags
        for prefix in all_prefixes.get(flag, [])
        if prefix.cond_regexp.search(word.stem) and similar_to.startswith(prefix.add)
    ]

    cross = [
        (prefix, suffix)
        for prefix in prefixes
        for suffix in suffixes
        if suffix.crossproduct and prefix.crossproduct
    ]

    for suf in suffixes:
        # FIXME: this things should be more atomic
        root = word.stem[0:-len(suf.strip)] if suf.strip else word.stem
        res.append(root + suf.add)

    for pref, suf in cross:
        root = word.stem[len(pref.strip):-len(suf.strip)] if suf.strip else word.stem[len(pref.strip):]
        res.append(pref.add + root + suf.add)

    for pref in prefixes:
        root = word.stem[len(pref.strip):]
        res.append(pref.add + root)

    return res


def filter_guesses(guesses: List[Tuple[float, str]], *, known: Set[str], onlymaxdiff=True) -> Iterator[str]:
    """
    Filter guesses by score, to decide which ones we'll yield to the client, considering the "suggestion
    bags" -- "very good", "normal", "questionable" (see :meth:`precise_affix_score` for bags definition).

    Args:
        guesses: All possible suggestions
        known: Passed from main Suggest, list of already produced suggestions
        onlymaxdiff: contents of :attr:`Aff.ONLYMAXDIFF <spylls.hunspell.data.aff.Aff.ONLYMAXDIFF>`
                     (exlcudes not very good suggestions, see code)
    """

    seen = False
    found = 0

    for (score, value) in guesses:
        if seen and score <= 1000:
            return

        if score > 1000:
            # If very good suggestion exists, we set the flag so that only other very good suggestions
            # would be returned, and then the cycle would stop
            seen = True
        elif score < -100:
            # If we found first questionable suggestion,
            # we stop immediately if there were any better suggestion, or if aff.ONLYMAXDIFF says
            # to avoid questionable ones alltogether
            if found > 0 or onlymaxdiff:
                return

            # ...and then we set flag so the cycle would end on
            # the next pass (suggestions are sorted by score, so everythig below is questionable, too,
            # and we allow only one suggestion from "questionable" bag)
            seen = True

        # This condition, and ``found`` variable somewhat duplicates tracking of found suggestions
        # in the main suggest cycle. It is this way because we need a counter of "how many ngram-based
        # suggestions were yielded and successfully consumed", to decide whether we want "questionable
        # ngram-suggestions" at all.
        # (Another possible approach is to return pairs (suggestion, quality) from ngram_suggest,
        # and handle "how many good/normal/questionable do we want" in main suggest.py)
        if not any(known_word in value for known_word in known):
            found += 1

            yield value
