import os.path

from spyll.hunspell.dictionary import Dictionary

def test_word(dic, w):
    found = dic.lookup(w)
    print(f'  {w}: {len(found)}')

def test_word2(dname, w):
    path = f'tests/fixtures/hunspell-orig/{dname}'
    d = Dictionary(path)
    test_word(d, w)

def count_found(dic, words):
    return [True for word in words if len(dic.lookup(word)) > 0].count(True)

def readlist(path):
    if not os.path.isfile(path):
        return []
    # we ignore "incomplete tokenization" feature
    return [ln for ln in open(path).read().splitlines() if ln[-1:] != '.' and ln != '']

def test(name):
    path = f'tests/fixtures/hunspell-orig/{name}'
    d = Dictionary(path)
    good = readlist(path + '.good')
    bad = readlist(path + '.wrong')

    print(name)
    print("Good: ")
    for w in good: test_word(d, w)

    print("Bad: ")
    for w in bad: test_word(d, w)

def test2(name):
    path = f'tests/fixtures/hunspell-orig/{name}'
    d = Dictionary(path)
    good = readlist(path + '.good')
    bad = readlist(path + '.wrong')

    print(f"{name}: good {count_found(d, good)} of {len(good)}, bad {count_found(d, bad)} of {len(bad)}")

test2('base')                   # + basic suffixes/prefixes + capitalization
test2('base_utf')               # ± special chars, 1 fail with turkish "i" capitalized

test2('affixes')                # + just simple affixes

test2('allcaps')                # + fully capitalized forms: UNICEF'S ('s suffix) and OPENOFFICE.ORG (find OpenOffice.org in dictionary)
test2('allcaps2')               # + forbiddenword marks possible, but wrong form
test2('allcaps3')               # + more capitalization + suffix examples
test2('allcaps_utf')            # +

test2('flag')                   # + suffix having its own flag "I can have extra suffix"

# TODO: only if flag COMPLEXPREFIXES is set in the dictionary
test2('complexprefixes')        # + prefix that has other prefix
test2('complexprefixes2')       # + morphological analysis (ignored for now)
test2('complexprefixesutf')     # + prefix pairs, UTF chars

test2('condition')              # + complex conditions "what is suitable affix"
test2('condition_utf')          # + same, with UTF chars
test2('conditionalprefix')      # + prefix allowed depending on suffix

test2('circumfix')              # + mark prefix "it is possible if has a suffix" -- FIXME: weirdly works without special CIRCUFIXFLAG processing...

# TODO: better comments!
test2('needaffix')              # + "this affix needs affix" flag
test2('needaffix2')             # + "this affix needs affix" flag
test2('needaffix3')             # + "this affix needs affix" flag
test2('needaffix4')             # + "this affix needs affix" flag
test2('needaffix5')             # + "this affix needs affix" flag -- two at once

# TODO: test that WITHOUT the flag it is impossible
test2('fullstrip')              # + removes entire word text by suffix.

# Compounding
# ===========
test2('compoundflag')           # + basic "it can be compounding"
test2('onlyincompound')         # + some of word is ONLY can be in compound

test2('compoundaffix')          # + in compound, prefix only at begin, suffix only at end
test2('compoundaffix2')         # + affix with permit flag allowed inside!
test2('compoundaffix3')         # + forbid flag rewrites any permissions ("do not use in compounds at all!")

test2('compoundrule')
test2('compoundrule2')
test2('compoundrule3')
test2('compoundrule4')
test2('compoundrule5')
test2('compoundrule6') # FIXME: works, but takes too long
# test2('compoundrule7') # - "long" flags
# test2('compoundrule8') # - "numeric" flags

# # Edge cases and bugs
# # =================
# # test2('slash')                # - slash in words -- screened with \ in dictionary

print("\n----------")
test_word2('compoundrule6', "aabbbc")

