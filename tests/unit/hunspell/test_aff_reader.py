from spyll.hunspell.data import aff as a
from spyll.hunspell.readers import AffReader

def test_everything():
    reader = AffReader('tests/fixtures/everything.aff')
    aff = reader()

    assert aff.SET == 'UTF-8'
    assert aff.FLAG == 'short'

    assert aff.KEY == 'qwertyuiopå|asdfghjklæø|zxcvbnm'

    assert aff.CIRCUMFIX == a.Flag('f')
    assert aff.NEEDAFFIX == a.Flag('*')
    assert aff.FORBIDDENWORD == a.Flag('-')
    assert aff.NOSUGGEST == a.Flag('X')
    assert aff.MAXCPDSUGS == 0
    assert aff.COMPOUNDMIN == 1

    assert aff.REP == [
        ("^Ca$", "Ça"),
        ("^l", "l'"),
        ("^d", "d'"),
        ("^n", "n'"),
        ("^s", "s'")
    ]

    assert aff.MAP == [
        "aàâäAÀÂÄ",
        "eéèêëEÉÈÊË",
        "iîïyIÎÏY",
        "oôöOÔÖ",
        "uùûüUÙÛÜ",
        "cçCÇ"
    ]

    assert aff.AF == [
        (1, {'A', 'B'}),
        (2, {'B', 'C'}),
        (3, {'C', 'D'}),
        (4, {'D', 'E'}),
    ]

    assert aff.sfx == [
        a.Suffix(flag='H', crossproduct=False, strip='y', add='ieth', condition='y', flags={}),
        a.Suffix(flag='H', crossproduct=False, strip='', add='th', condition='[^y]', flags={})
    ]

    assert aff.pfx == [
        a.Prefix(flag='F', crossproduct=True, strip='', add='con', condition='.', flags={})
    ]

def test_encoding():
  pass

def test_long_flags():
  reader = AffReader('tests/fixtures/long_flags.aff')
  aff = reader()

def test_numeric_flags():
  reader = AffReader('tests/fixtures/long_flags.aff')
  aff = reader()

def test_utf8_flags():
  pass
