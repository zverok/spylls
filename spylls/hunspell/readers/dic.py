from collections import defaultdict
import re

from typing import List, Dict

from spylls.hunspell.data import dic
from spylls.hunspell.data.aff import Aff, RepPattern

from spylls.hunspell.readers.file_reader import BaseReader
from spylls.hunspell.readers.aff import Context

from spylls.hunspell.algo.capitalization import Type as CapType


COUNT_REGEXP = re.compile(r'^\d+(\s+|$)')   # should start with digits, but can have whatever further
SPACES_REGEXP = re.compile(r"\s+")
MORPH_REGEXP = re.compile(r'^(\w{2}:\S*|\d+)$')
SLASH_REGEXP = re.compile(r'(?<!\\)/')


def read_dic(source: BaseReader, *, aff: Aff, context: Context) -> dic.Dic:
    """
    Reads source (file or zipfile) and creates :class:`Dic <spylls.hunspell.data.dic.Dic>` from it.

    Args:
        source: "Reader" (thin wrapper around opened file or zipfile, targeting line-by-line reading)
        aff: Contents of corresponding .aff file. Note that this method can *mutate* passed
             ``aff`` by updating its :attr:`REP <spylls.hunspell.data.aff.Aff.REP>` table (pairs of
             typical misspelling and its replacement) with contents of dictionary's ``ph:`` data tag
        context: Context created while reading .aff file and defining common reading settings:
                 encoding, format of flags and chars to ignore.
    """
    result = dic.Dic(words=[])

    for num, line in source:
        if num == 1 and COUNT_REGEXP.match(line):
            continue

        word_parts = []
        data: Dict[str, List[str]] = defaultdict(list)

        parts = SPACES_REGEXP.split(line)

        # Each line is ``<stem>/<flags> <data tags>``
        # Stem can have spaces, data tags are separated from stem by spaces

        for i, part in enumerate(parts):
            # The only way to understand what's the next part:
            if ':' in part and i != 0:
                # If it has "foo:bar" form, it is data tag
                tag, _, content = part.partition(':')
                # TODO: in ph2.dic, there is "ph:" construct (without contents), what does it means?..
                if content:
                    data[tag].append(content)
            elif part.isdigit() and i != 0:
                # If it is just numeric AND not the first part in string, it is "morphology alias"
                # (defined in .aff file list of data tags corresponding to some number)
                # So we just mutate the list of parts we are currently processing, so those fetched
                # by numeric alias would be handled.
                parts.extend(aff.AM[part])
            else:
                # ...otherwise, it is still part of the word
                word_parts.append(part)

        word = ' '.join(word_parts)
        # Now, the "word" part is "stem/flags". Flags are optional, and to complicate matters further:
        #
        # * if the word STARTS with "/" -- it is not empty stem + flags, but "word starting with /";
        # * if the "/" should be in stem, it can be screened by "\/"
        if word.startswith('/'):
            flags = ''
        else:
            word_with_flags = SLASH_REGEXP.split(word, 2)
            if len(word_with_flags) == 2:
                word, flags = word_with_flags
            else:
                flags = ''

        if r'\/' in word:
            word = word.replace(r'\/', '/')

        # Here we have our clean word (with screened "\/" replaced, and flag splitted off)

        if context.ignore:
            # ...now we remove any chars context says to ignore...
            word = word.translate(context.ignore.tr)

        # And cache word's casing and its lowerase form
        captype = aff.casing.guess(word)
        lower = aff.casing.lower(word) if captype != CapType.NO else word

        alt_spellings = []

        if 'ph' in data:
            # Now, for all "ph:" (alt.spellings) patterns:

            for pattern in data['ph']:
                # TODO: https://manpages.debian.org/experimental/libhunspell-dev/hunspell.5.en.html#Optional_data_fields
                # according to it, Wednesday ph:wendsay should produce two cases
                #   REP wendsay Wednesday
                #   REP Wendsay Wednesday
                # hunspell handles it by just `if (captype==INITCAP)`...
                if pattern.endswith('*'):
                    # If it is ``pretty ph:prit*`` -- it means pair ``(prit, prett)`` should be added
                    # to REP-table
                    aff.REP.append(RepPattern(pattern[:-2], word[:-1]))
                elif '->' in pattern:
                    # If it is ``happy ph:hepi->happi`` -- it means pair ``(hepi, happi)`` should be added
                    # to REP-table ("happy" itself is just ignored...)
                    fro, _, to = pattern.partition('->')
                    aff.REP.append(RepPattern(fro, to))
                else:
                    # And if it is simple ``wednesday ph:wensday``, it means that ``(wensday, wednesday)``
                    # should be added to REP table
                    aff.REP.append(RepPattern(pattern, word))
                    # ...and that "wensday" should be stored in word as alt.spelling (used for ngram suggest)
                    alt_spellings.append(pattern)

        # And here we are!
        word_obj = dic.Word(
            stem=word,
            flags={*context.parse_flags(flags)},
            data=data,
            captype=captype,
            alt_spellings=alt_spellings
        )
        result.append(word_obj, lower=lower)

    return result
