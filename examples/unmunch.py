# This is "unmunching" script for Hunspell dictionaries, based on Spylls (full Python port of Hunspell):
# https://github.com/zverok/spylls
#
# "Unmunching" (Hunspell's term) is a process of turning affix-compressed dictionary into plain list
# of all language's words. E.g. for English, in the dictionary we have "spell/JSMDRZG" (stem + flags
# declaring what suffixes and prefixes it might have), and we can run this script:
#
#   python unmunch.py path/to/en_US spell
#
# Which will produce this list:
#
#   spell
#   spell's
#   spelled
#   speller
#   spellers
#   spelling
#   spellings
#   spells
#
# Running without second argument will unmunch the entire dictionary.
#
# WARNINGS!
#
#  1. The script is not extensively tested, just a demo for discussion in https://github.com/zverok/spylls/issues/10
#     (see the issue for more discussion)
#  2. It doesn't try to produce all possible words for compounding, because the list is potentiall infinite.
#

import sys
from optparse import OptionParser

from spylls.hunspell.dictionary import Dictionary

parser = OptionParser()
parser.add_option("-d", "--dictionary", dest="dictionary", metavar='DICTIONARY',
                  help="dictionary path to unmunch (<path>.aff and <path>.dic should be present)")
parser.add_option("-w", "--word", dest="word", default=None, metavar='WORD',
                  help="singular word to unmunch (if absent, unmunch the whole dictionary")
parser.add_option("-i", "--immediate", dest="immediate", default=False, action='store_true',
                  help="output unmunch for each word immediately (more memory-effective, but not sorted and might contain duplicates)")

(options, args) = parser.parse_args()

dictionary = Dictionary.from_files(options.dictionary)

def unmunch(word, aff):
    result = set()

    if aff.FORBIDDENWORD and aff.FORBIDDENWORD in word.flags:
        return result

    if not (aff.NEEDAFFIX and aff.NEEDAFFIX in word.flags):
        result.add(word.stem)

    suffixes = [
        suffix
        for flag in word.flags
        for suffix in aff.SFX.get(flag, [])
        if suffix.cond_regexp.search(word.stem)
    ]
    prefixes = [
        prefix
        for flag in word.flags
        for prefix in aff.PFX.get(flag, [])
        if prefix.cond_regexp.search(word.stem)
    ]

    for suffix in suffixes:
        root = word.stem[0:-len(suffix.strip)] if suffix.strip else word.stem
        suffixed = root + suffix.add
        if not (aff.NEEDAFFIX and aff.NEEDAFFIX in suffix.flags):
            result.add(suffixed)

        if suffix.crossproduct:
            additional_prefixes = [
                prefix
                for flag in suffix.flags
                for prefix in aff.PFX.get(flag, [])
                if prefix.crossproduct and not prefix in prefixes and prefix.cond_regexp.search(suffixed)
            ]
            for prefix in prefixes + additional_prefixes:
                root = suffixed[0:-len(prefix.strip)] if prefix.strip else suffixed
                prefixed = prefix.add + root
                result.add(prefixed)

                secondary_prefixes = [
                    prefix2
                    for flag in prefix.flags
                    for prefix2 in aff.PFX.get(flag, [])
                    if prefix2.crossproduct and prefix2.cond_regexp.search(prefixed)
                ]
                for prefix2 in secondary_prefixes:
                    root = prefixed[0:-len(prefix2.strip)] if prefix2.strip else prefixed
                    result.add(prefix2.add + root)

        secondary_suffixes = [
            suffix2
            for flag in suffix.flags
            for suffix2 in aff.SFX.get(flag, [])
            if suffix2.cond_regexp.search(suffixed)
        ]
        for suffix2 in secondary_suffixes:
            root = suffixed[0:-len(suffix2.strip)] if suffix2.strip else suffixed
            result.add(root + suffix2.add)

    for prefix in prefixes:
        root = word.stem[len(prefix.strip):]
        prefixed = prefix.add + root
        if not (aff.NEEDAFFIX and aff.NEEDAFFIX in prefix.flags):
            result.add(prefixed)

        if prefix.crossproduct:
            additional_suffixes = [
                suffix
                for flag in prefix.flags
                for suffix in aff.SFX.get(flag, [])
                if suffix.crossproduct and not suffix in suffixes and suffix.cond_regexp.search(prefixed)
            ]
            for suffix in suffixes + additional_suffixes:
                root = prefixed[0:-len(suffix.strip)] if suffix.strip else prefixed
                suffixed = root + suffix.add
                result.add(suffixed)

                secondary_suffixes = [
                    suffix2
                    for flag in suffix.flags
                    for suffix2 in aff.SFX.get(flag, [])
                    if suffix2.crossproduct and suffix2.cond_regexp.search(suffixed)
                ]
                for suffix2 in secondary_suffixes:
                    root = suffixed[0:-len(suffix2.strip)] if suffix2.strip else suffixed
                    result.add(root + suffix2.add)

    return result

result = set()

if options.word:
    lookup = options.word
    print(f"Unmunching only words with stem {lookup}", file=sys.stderr)
else:
    lookup = None
    print(f"Unmunching the whole dictionary", file=sys.stderr)

print('', file=sys.stderr)

for word in dictionary.dic.words:
    if not lookup or word.stem == lookup:
        if lookup:
            print(f"Unmunching {word}", file=sys.stderr)
            pass
        if options.immediate:
            for word in sorted(unmunch(word, dictionary.aff)):
                print(word)
        else:
            result.update(unmunch(word, dictionary.aff))

print('', file=sys.stderr)

if not options.immediate:
    for word in sorted(result):
        print(word)
