from spyll.hunspell.data import aff

from spyll.hunspell.algo import Stemmer

def test_desuffix():
    suffixes = [
        aff.Suffix(flag='S', crossproduct=False, strip='y', add='ies', condition='[^aeiou]y'),
        aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[aeiou]y'),
        aff.Suffix(flag='S', crossproduct=False, strip='', add='es', condition='[sxzh]'),
        aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[^sxzhy]'),

        aff.Suffix(flag='X', crossproduct=True, strip='', add='ens', condition='[^ey]')
    ]
    stemmer = Stemmer(suffixes=suffixes)

    assert stemmer.desuffix('cat') == []

    assert stemmer.desuffix('cats') == [
        ('cat', aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[^sxzhy]'))
    ]

    assert stemmer.desuffix('buses') == [
        ('bus', aff.Suffix(flag='S', crossproduct=False, strip='', add='es', condition='[sxzh]'))
    ]

    assert stemmer.desuffix('kitties') == [
        ('kitty', aff.Suffix(flag='S', crossproduct=False, strip='y', add='ies', condition='[^aeiou]y'))
    ]

    assert stemmer.desuffix('decoys') == [
        ('decoy', aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[aeiou]y'))
    ]

    # multiple candidates
    # Note that neither of candiates is a valid stem, but it is not stemmer's responsibility to check
    assert stemmer.desuffix('lens') == [
        ('len', aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[^sxzhy]')),
        ('l', aff.Suffix(flag='X', crossproduct=True, strip='', add='ens', condition='[^ey]')),
    ]
