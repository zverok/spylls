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

def section(title):
    print()
    print(title)
    print('=' * len(title))

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


# ==============================
section('Base')

report('base')                   # + basic suffixes/prefixes + capitalization
report('base_utf')               # ± special chars, 1 fail with turkish "i" capitalized

report('flag')                   # + suffix having its own flag "I can have extra suffix"
# report('flaglong')
# report('flagnum')
# report('flagutf8')
# report('alias')
# report('alias2')
# report('alias3')
report('encoding')
report('utf8')
# report('utf8_bom')    # TODO: file reader support for BOM
# report('utf8_bom2')   # TODO: file reader support for BOM
# report('right_to_left_mark') # TODO: file reader should remove \u200f

# ===============================
section('Affixes')

report('affixes')                # + just simple affixes

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

report('zeroaffix')


# ==============================
section("Exclusion flags")

report('allcaps')                # + fully capitalized forms: UNICEF'S ('s suffix) and OPENOFFICE.ORG (find OpenOffice.org in dictionary)
report('allcaps2')               # + forbiddenword marks possible, but wrong form
report('allcaps3')               # + more capitalization + suffix examples
report('allcaps_utf')            # +
report('forbiddenword')
report('keepcase')
report('nosuggest')

# ==============================
section('Break')

report('breakdefault')
report('break')
report('breakoff')

# ==============================
section('Input/Output')

report('iconv')
report('iconv2')
report('oconv')
report('oconv2')

# ==============================
section('Compounding')

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

report('checkcompoundcase')
report('checkcompoundcase2')
report('checkcompoundcaseutf')
report('checkcompounddup')
report('checkcompoundpattern')
# report('checkcompoundpattern2') -- replacement feature of pattern seems to not be used at all
# report('checkcompoundpattern3')
# report('checkcompoundpattern4')
report('checkcompoundrep')
report('checkcompoundtriple')
report('compoundforbid')

report('simplifiedtriple')

report('wordpair')
report('forceucase')
report('utfcompound')

# ======================================
section('Misc')

report('fogemorpheme')
report('morph')
report('ngram_utf_fix')
report('opentaal_cpdpat')
report('opentaal_cpdpat2')
report('opentaal_forbiddenword1')
report('opentaal_forbiddenword2')
# report('opentaal_keepcase') -- reader fail, `break #`
report('ph2')

report('utf8_nonbmp')
report('warn')


# ===============================
section('Specific languages')

report('ignore')
report('ignoresug')
report('ignoreutf')
report('germancompounding')
report('germancompoundingold')
report('hu')
report('dotless_i')            # - turkish capitalization rules
report('IJ')
report('nepali')
report('korean')
report('checksharps')
report('checksharpsutf')

# ===============================
section('Edge cases and bugs')

# report('slash')                # - slash in words -- screened with \ in dictionary
# report('timelimit')

# report('1592880')
# report('1975530')
# report('2970240')
# report('2970242')
# report('2999225')
# report('i35725')
# report('i53643')
# report('i54633')
# report('i54980')
# report('i58202')
