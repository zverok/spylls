hunspell.cpp:
  spell -> (ifcorrect, ifcompound, ifforbidden, root)
    after all: root: use oconv
    → use iconv
    → cleanword2
      remove leading blanks
      remove trailing periods (set flags it was there)
      → guess capitalization type
        no capitalized chars: nocap
        only first char: initcap
        all (capitalized or "neutral"): allcap
        first char & some other: huhinitcap
        some: huhcap
    allow 1234,6444- and so on (but not doubled separators)
    on captype
      HUHCAP/HUHINITCAP adds SPELL_ORIGCAP flag to context
      + NOCAP: checks word (with and without end dot)
      ALLCAP
        adds SPELL_ORIGCAP flag to context
        checks with and without dot
        if apostrophe → super-complicated handling of (Catalan, French, Italian) apostrophed prefix
        handling of ssharp
      + INITCAP
        (handle dotted I)
        check exactly this (don't forget to check if the form's forbidden)
        stop if found, or have dotted I and lang in (az, tr, crh)
        check if capitalized found (with dot, too)
        ...handle SS a bit :)
        * check if warning should be added
    if nothing found: try breaking the word!
      wordbreak is BREAK from .aff (what chars we can break on)
  checkword
    remove IGNORE chars (ex: arab diacritics)
    lookup this word on hashtable of words
      select a homonym that is not forbidden and not "onlyincompound" and not onlyupcase and not needaffix
    check with affixes stripped
      → AffixMgr::affix_check
      ← reject onlyincompound, or onlyupcase, or forbidden
    check compound
      if either COMPOUNDFLAG, or COMPOUNDBEG, or COMPOUNDRULE is present
      → AffixMgr::compound_check

affixmgr.cxx:
  affix_check
    prefix_check
      (including cross with suffixes)
      1. check all 0-length prefixes (indexed by 0)
      2. check regular prefixes (indexed by first letter)
      uses Prefix::check_word
    suffix_check
    suffix_check_twosfx
    prefix_check_twosfx
  compound_check
    default compound word min size = 3

affentry.cxx:
  Prefix::check_word
    chops off append
    adds strip
    tests whether resulting word matches to condition
    (if production allowed and word not in the dictionary, checks resulting word with suffixes)
