from spyll.hunspell.data import aff

from spyll.hunspell.algo import Stemmer
from spyll.hunspell.algo import stemmer as st

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

def test_depreffix():
    # TODO: test it better. Current test data is taken from en_US.aff, and English is not very
    # fancy around suffixes...
    prefixes = [
        aff.Prefix(flag='S', crossproduct=False, strip='', add='un', condition='.'),
    ]
    stemmer = Stemmer(prefixes=prefixes)

    assert stemmer.deprefix('cat') == []
    assert stemmer.deprefix('uncat') == [
        ('cat', aff.Prefix(flag='S', crossproduct=False, strip='', add='un', condition='.')),
    ]

def test_call():
    suffixes = [
        aff.Suffix(flag='S', crossproduct=False, strip='y', add='ies', condition='[^aeiou]y'),
        aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[aeiou]y'),
        aff.Suffix(flag='S', crossproduct=False, strip='', add='es', condition='[sxzh]'),
        aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[^sxzhy]'),

        aff.Suffix(flag='D', crossproduct=True, strip='', add='d', condition='e')
    ]
    prefixes = [
        aff.Prefix(flag='S', crossproduct=True, strip='', add='un', condition='.'),
    ]
    stemmer = Stemmer(suffixes=suffixes, prefixes=prefixes)

    assert stemmer('cat') == [
        st.Result('cat')
    ]

    # Only suffix exists
    assert stemmer('cats') == [
        st.Result('cats'),
        st.Result('cat', suffix=aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[^sxzhy]'))
    ]

    # Prefix and suffix exist, but they are NOT combinable:
    assert stemmer('uncats') == [
        st.Result('uncats'),
        st.Result('uncat', suffix=aff.Suffix(flag='S', crossproduct=False, strip='', add='s', condition='[^sxzhy]')),
        st.Result('cats', prefix=aff.Prefix(flag='S', crossproduct=True, strip='', add='un', condition='.'))
    ]

    # Prefix and suffix, combinable
    assert stemmer('unsaved') == [
        st.Result('unsaved'),
        st.Result('unsave', suffix=aff.Suffix(flag='D', crossproduct=True, strip='', add='d', condition='e')),
        st.Result('saved', prefix=aff.Prefix(flag='S', crossproduct=True, strip='', add='un', condition='.')),
        st.Result('save',
            prefix=aff.Prefix(flag='S', crossproduct=True, strip='', add='un', condition='.'),
            suffix=aff.Suffix(flag='D', crossproduct=True, strip='', add='d', condition='e')
        )
    ]
