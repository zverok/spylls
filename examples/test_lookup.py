import os.path

from spyll.hunspell.dictionary import Dictionary

def readlist(path, ignoredot=True):
    if not os.path.isfile(path):
        return []
    # we ignore "incomplete tokenization" feature
    return [ln for ln in open(path).read().splitlines() if not ignoredot or ln[-1:] != '.']

def test(name):
    path = f'tests/fixtures/hunspell-orig/{name}'
    dictionary = Dictionary(path)
    good = readlist(path + '.good')
    bad = readlist(path + '.wrong')
    return {
        'good': {word: dictionary.lookup(word) for word in good if word},
        'bad': {word: dictionary.lookup(word) for word in bad},
    }

def report(name):
    # print(name)

    result = test(name)
    good = result['good']
    nogood = [word for word, res in good.items() if not res]

    bad = result['bad']
    nobad = [word for word, res in bad.items() if res]

    summary = f"{name}: "
    if nogood:
        summary += f"good fail ({len(nogood)} of {len(good)})"
    else:
        summary += f"good OK ({len(good)})"

    if bad:
        if nobad:
            summary += f", bad fail ({len(nobad)} of {len(bad)})"
        else:
            summary += f", bad OK ({len(bad)})"

    print(summary)
    if nogood:
        print(f"  Good words not found: {', '.join(nogood)}")
    if nobad:
        print(f"  Bad words found: {', '.join(nobad)}")


report('base')                   # + basic suffixes/prefixes + capitalization
report('base_utf')               # ± special chars, 1 fail with turkish "i" capitalized

report('affixes')                # + just simple affixes

report('allcaps')                # + fully capitalized forms: UNICEF'S ('s suffix) and OPENOFFICE.ORG (find OpenOffice.org in dictionary)
report('allcaps2')               # + forbiddenword marks possible, but wrong form
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
# report('onlyincompound2')      # - checkcompoundpattern

report('compoundaffix')          # + in compound, prefix only at begin, suffix only at end
report('compoundaffix2')         # + affix with permit flag allowed inside!
report('compoundaffix3')         # + forbid flag rewrites any permissions ("do not use in compounds at all!")

# TODO: Explanations!
report('compoundrule')
report('compoundrule2')
report('compoundrule3')
report('compoundrule4')
report('compoundrule5')
report('compoundrule6')
# report('compoundrule7') # - "long" flags
# report('compoundrule8') # - "numeric" flags

report('breakdefault')
report('break')
report('breakoff')

report('checkcompoundcase2')
report('checkcompoundcase')
report('checkcompoundcaseutf')
report('checkcompounddup')
report('checkcompoundpattern2')
report('checkcompoundpattern3')
report('checkcompoundpattern4')
report('checkcompoundpattern')
report('checkcompoundrep')
report('checkcompoundtriple')
report('checksharps')
report('checksharpsutf')

report('compoundforbid')
report('dotless_i')
report('encoding')

# report('flag')
# report('flaglong')
# report('flagnum')
# report('flagutf8')
# report('alias')
# report('alias2')
# report('alias3')

report('fogemorpheme')
report('forbiddenword')
report('forceucase')
report('germancompounding')
report('germancompoundingold')
report('hu')
report('iconv2')
report('iconv')
report('ignore')
report('ignoresug')
report('ignoreutf')
report('IJ')
report('keepcase')
report('korean')
report('morph')
report('nepali')
report('ngram_utf_fix')
report('nosuggest')
report('oconv2')
report('oconv')
report('opentaal_cpdpat2')
report('opentaal_cpdpat')
report('opentaal_forbiddenword1')
report('opentaal_forbiddenword2')
report('opentaal_keepcase')
report('ph2')
report('right_to_left_mark')
report('simplifiedtriple')

report('utf8_bom2')
report('utf8_bom')
report('utf8')
report('utf8_nonbmp')
report('utfcompound')
report('warn')
report('wordpair')
report('zeroaffix')

# Edge cases and bugs
# =================
# report('slash')                # - slash in words -- screened with \ in dictionary
# report('timelimit')

report('1592880')
report('1975530')
report('2970240')
report('2970242')
report('2999225')
report('i35725')
report('i53643')
report('i54633')
report('i54980')
report('i58202')
