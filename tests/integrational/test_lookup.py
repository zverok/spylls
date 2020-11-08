import time
import sys
from collections import Counter

from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from base import read_list, read_dictionary, section, summary

stats = Counter()

def test(name):
    dictionary = read_dictionary(name)
    good = read_list(f'{name}.good')
    bad = read_list(f'{name}.wrong')

    # morph.good has "drink eat" pairs, which hunspell treats as just two words :shrug:
    def lookup(word):
        res = dictionary.lookup(word)
        if ' ' in word and not res:
            res = all(dictionary.lookup(w) for w in word.split(' '))
        return res

    return {
        'good': {word: lookup(word) for word in good if word},
        'bad': {word: lookup(word) for word in bad},
    }

def report(name, pending_comment=None):
    global stats

    stats['total'] += 1

    if pending_comment:
        stats['pending'] += 1
        print(f"*{name}: pending {'' if pending_comment is True else '(' + pending_comment + ')'}")
        return

    start = time.monotonic()
    result = test(name)
    duration = time.monotonic() - start

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

    if duration > 0.05:
        summary += f" [{duration:.4f}s]"
        stats['slow'] += 1

    print(summary)
    if nogood:
        print(f"  Good words not found: {', '.join(nogood)}")
    if nobad:
        print(f"  Bad words found: {', '.join(nobad)}")
    if nogood or nobad:
        stats['fail'] += 1
    else:
        stats['ok'] += 1


# ==============================
section('Base')

report('base')                   # + basic suffixes/prefixes + capitalization
report('base_utf')               # ± special chars, 1 fail with turkish "i" capitalized

report('flag')                   # + suffix having its own flag "I can have extra suffix"
report('flaglong')
report('flagnum')
report('flagutf8')
report('alias')
report('alias2')
report('alias3')
report('encoding')
report('utf8')
report('utf8_bom')
report('utf8_bom2')
report('right_to_left_mark')

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

report('circumfix')              # + mark prefix "it is possible if has a suffix" -- FIXME: weirdly works without special CIRCUMFIXFLAG processing...

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
report('onlyincompound2', pending_comment='replacement in pattern')        # - checkcompoundpattern

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
report('compoundrule7')
report('compoundrule8')

report('checkcompoundcase')
report('checkcompoundcase2')
report('checkcompoundcaseutf')
report('checkcompounddup')
report('checkcompoundpattern')
report('checkcompoundpattern2', pending_comment='replacement in pattern') # replacement feature of pattern seems to not be used at all
report('checkcompoundpattern3', pending_comment='replacement in pattern')
report('checkcompoundpattern4', pending_comment='replacement in pattern')
report('checkcompoundrep')
report('checkcompoundtriple')
report('compoundforbid')

report('simplifiedtriple')

report('wordpair')
report('forceucase')
report('utfcompound')

report('fogemorpheme')

report('opentaal_cpdpat')
report('opentaal_cpdpat2')

report('opentaal_forbiddenword1')
report('opentaal_forbiddenword2')

# ======================================
section('Misc')

report('ngram_utf_fix')

report('opentaal_keepcase')

report('ph2')
report('morph')

report('utf8_nonbmp')
report('warn')


# ===============================
section('Specific languages')

report('ignore')
report('ignoresug')
report('ignoreutf')

report('checksharps')
report('checksharpsutf')

report('dotless_i')             # + turkish capitalization rules
report('IJ')

report('nepali')                # - conversion of invisible characters
report('korean')

report('germancompounding')
report('germancompoundingold')
report('hu', pending_comment='Hungarian is hard!')

# ===============================
section('Edge cases and bugs')

report('slash')
report('timelimit', pending_comment=True)

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

summary(stats)
