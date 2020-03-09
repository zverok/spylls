import os.path

from spyll.hunspell.readers import AffReader, DicReader
from spyll.hunspell.algo import lookup

def test_word(aff, dic, w, detailed=False):
    found = lookup.analyze(aff, dic, w)
    if detailed:
        print(f'  {w}: {list(found)}')
    else:
        print(f'  {w}: {len(list(found))}')

def test_word2(dname, w, detailed=False):
    path = f'tests/fixtures/hunspell-orig/{dname}'
    aff = AffReader(path + '.aff')()
    dic = DicReader(path + '.dic', encoding = aff.set, flag_format = aff.flag)()
    test_word(aff, dic, w, detailed=detailed)

def count_found(dic, words):
    return [True for word in words if len(dic.lookup(word)) > 0].count(True)

def readlist(path):
    if not os.path.isfile(path):
        return []
    # we ignore "incomplete tokenization" feature
    return [ln for ln in open(path).read().splitlines() if ln[-1:] != '.' and ln != '']

# def test(name):
#     path = f'tests/fixtures/hunspell-orig/{name}'
#     d = Dictionary(path)
#     good = readlist(path + '.good')
#     bad = readlist(path + '.wrong')

#     print(name)
#     print("Good: ")
#     for w in good: test_word(d, w)

#     print("Bad: ")
#     for w in bad: test_word(d, w)

# def report(name):
#     path = f'tests/fixtures/hunspell-orig/{name}'
#     d = Dictionary(path)
#     good = readlist(path + '.good')
#     bad = readlist(path + '.wrong')

#     print(f"{name}: good {count_found(d, good)} of {len(good)}, bad {count_found(d, bad)} of {len(bad)}")


def test(name):
    path = f'tests/fixtures/hunspell-orig/{name}'
    aff = AffReader(path + '.aff')()
    dic = DicReader(path + '.dic', encoding = aff.set, flag_format = aff.flag)()
    good = readlist(path + '.good')
    bad = readlist(path + '.wrong')
    return {
        'good': {word: lookup.lookup(aff, dic, word) for word in good},
        'bad': {word: lookup.lookup(aff, dic, word) for word in bad},
    }

def report(name):
    print(name)

    result = test(name)
    good = result['good']
    nogood = [word for word, res in good.items() if not res]
    if nogood:
        print(f"  Good: {len(good) - len(nogood)} of {len(good)}")
        print(f"    not found: {', '.join(nogood)}")
    else:
        print(f"  Good: {len(good)}")

    bad = result['bad']
    nobad = [word for word, res in bad.items() if res]
    if nobad:
        print(f"  Bad: {len(nobad)} of {len(bad)}")
        print(f"    found: {', '.join(nobad)}")
    else:
        print(f"  Bad: {len(bad)}")


report('base')                   # + basic suffixes/prefixes + capitalization
report('base_utf')               # ± special chars, 1 fail with turkish "i" capitalized

report('affixes')                # + just simple affixes

report('allcaps')                # + fully capitalized forms: UNICEF'S ('s suffix) and OPENOFFICE.ORG (find OpenOffice.org in dictionary)
# report('allcaps2')               # + forbiddenword marks possible, but wrong form
report('allcaps3')               # + more capitalization + suffix examples
report('allcaps_utf')            # +

report('flag')                   # + suffix having its own flag "I can have extra suffix"

# TODO: only if flag COMPLEXPREFIXES is set in the dictionary
report('complexprefixes')        # + prefix that has other prefix
report('complexprefixes2')       # + morphological analysis (ignored for now)
report('complexprefixesutf')     # + prefix pairs, UTF chars

report('condition')              # + complex conditions "what is suitable affix"
report('condition_utf')          # + same, with UTF chars
report('conditionalprefix')      # + prefix allowed depending on suffix

report('circumfix')              # + mark prefix "it is possible if has a suffix" -- FIXME: weirdly works without special CIRCUFIXFLAG processing...

# TODO: better comments!
report('needaffix')              # + "this affix needs affix" flag
report('needaffix2')             # + "this affix needs affix" flag
report('needaffix3')             # + "this affix needs affix" flag
report('needaffix4')             # + "this affix needs affix" flag
report('needaffix5')             # + "this affix needs affix" flag -- two at once

# TODO: test that WITHOUT the flag it is impossible
report('fullstrip')              # + removes entire word text by suffix.

# Compounding
# ===========
report('compoundflag')           # + basic "it can be compounding"
report('onlyincompound')         # + some of word is ONLY can be in compound

report('compoundaffix')          # + in compound, prefix only at begin, suffix only at end
report('compoundaffix2')         # + affix with permit flag allowed inside!
report('compoundaffix3')         # + forbid flag rewrites any permissions ("do not use in compounds at all!")

report('compoundrule')
report('compoundrule2')
report('compoundrule3')
report('compoundrule4')
report('compoundrule5')
report('compoundrule6') # FIXME: works, but takes too long
report('compoundrule7') # - "long" flags
report('compoundrule8') # - "numeric" flags

# # Edge cases and bugs
# # =================
# # report('slash')                # - slash in words -- screened with \ in dictionary

# test_word2('base', 'created', True)
