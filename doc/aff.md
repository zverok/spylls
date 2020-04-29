## General

Initial source: https://www.systutorials.com/docs/linux/man/4-hunspell/

SET (encoding)
FLAG (UTF-8,num,long) -- 1 char is default, num (number) or long (2 chars)
  decimal flags are comma-separated
  da,ko: num; fr,ka: long
LANG langcode -- special fun
  Azeri (LANG az) and Turkish (LANG tr).
IGNORE characters -- optional diacritics
  ar
AF: array of alias for flag set. position makes its name (number), string lists affixes
  hu,ko,fr,ar

## Suggestion

KEY abc|edf|foobarbaz -- use "neighbour" chars to replace (in fact, it is keyboard layout?)
  da, fr, hu
TRY abfsd -- when trying to insert one (probably forgotten) char, try them in this order
  everywhere
NOSUGGEST flag -- don't suggest word
  everywhere
MAXCPDSUGS -- max num of suggested compounds
  da -- 0
MAXNGRAMSUGS -- max number of n-grams (?)
  —
MAXDIFF [0-10] -- for n-gram based
  hi_IN
ONLYMAXDIFF -- remove bad n-grams
  —
NOSPLITSUGS -- don't suggest splits
  —
SUGSWITHDOTS -- add dots to suggestion
  —
REP -- array of pairs, try to replace "f" with "ph", from could be regexp, "_" should be used instead of " "
  everywhere
MAP -- array of "similar chars" sets
  lots
PHONE -- phonetic replacements
  —
WARN flag -- rare word
  —
FORBIDWARN -- make WARN words forbidden
  —

## Compounding

BREAK -- array of breakpoints (regexp allowed), can be also used to remove punct at the beg/end
  de,fr,hu

COMPOUNDRULE -- array of patterns, `flag*flag?(flag)`
  en,hu,ko
COMPOUNDMIN -- minimum length of compounding word
  lots
COMPOUNDFLAG flag -- "can be compounded"
  hu,nb,nn
COMPOUNDBEGIN flag -- begin of compound
  da,de,hu
COMPOUNDLAST flag
  hu
COMPOUNDMIDDLE flag
  da,de
ONLYINCOMPOUND flag -- suffixes that only can be in compound words
  da,de,en,hu
COMPOUNDPERMITFLAG flag -- affix allowed inside of compound
  da,de,hu
COMPOUNDFORBIDFLAG flag -- affix not allowed with compound at all
  hu
COMPOUNDROOT flag -- root of compound
  hu
COMPOUNDWORDMAX number -- maximum number of components
  da hu
CHECKCOMPOUNDDUP -- forbid dup in compound
  hu
CHECKCOMPOUNDREP -- not a compound, if REP replacement gives the right word
  hu
CHECKCOMPOUNDCASE -- no uppercase in the middle
  hu
CHECKCOMPOUNDTRIPLE -- forbid triple letter
  hu
SIMPLIFIEDTRIPLE -- allow to squise triple into double on compounding
  —
CHECKCOMPOUNDPATTERN -- array of `endchars[/flag] beginchars[/flag] [replacement]` -- forbid specific compounding
  hu
FORCEUCASE flag -- that compound part existing forces word to be upcase
  —
COMPOUNDSYLLABLE -- something very hungarian
  hu
SYLLABLENUM flags -- also

## Stemming

PFX flag cross_product number
PFX flag stripping prefix [condition [morphological_fields...]]
SFX flag cross_product number
SFX flag stripping suffix [condition [morphological_fields...]]

COMPLEXPREFIXES -- try strip prefix 2 times
  —
CIRCUMFIX flag -- allows suffix to be in word with another prefix, marked with same flag
  de,fr,ca
FULLSTRIP -- affixes can remove all the word
  —
NEEDAFFIX flag -- roots that needs affixes, aka PSEUDOROOT
  da,de,fr,hu,ka
FORBIDDENWORD flag -- forbidden word form, used to mark erroneous possible compounds/suffixed forms
  da,de,fr,hu,ka,ko
KEEPCASE flag -- never try other cases
  de,fr,hu
CHECKSHARPS -- german ss

NB: prefix/suffix can have flags!
NB: prefix can have morphology! (see conditionalprefixes test)

## IO

ICONV -- array of (from, to) -- useful for ligatures and "too much Unicode"
  fr,hu,ko
OCONV -- array of (from, to) -- ?prettify suggestions; in fr, converts ' to ’
  fr,ko
WORDCHARS characters -- add other chars that should be considered words to tokenizer
  da,de,en,fr,hu,ko

## Morphological analysis/generation

In `*.dic`: `word/flags po:noun is:nom`, or `*.aff`: `SFX X 0 able . ds:able`

AM: array of alias for morph rule set
SUBSTANDARD flag -- not used in morphological generation
  hu

LEMMA_PRESENT flag -- deprecated
  hu
