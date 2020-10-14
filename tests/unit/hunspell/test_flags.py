@pytest.mark.parametrize(
    ({}, 'cat', None, None, ''),
    ({needaffix='X'}, 'cat', None, None, '!X'), # Flag needaffix should be absent
    ({}, 'cat', Suffix('S', 's'), None, 'S'),
    ({}, 'cat', Suffix('S', 's'), Prefix('A', 'anti'), 'A&S'),
    ({needsaffix='X'}, 'cat', Suffix('S', 's'), Prefix('A', 'anti'), 'A&S'),
)
def test_affix_flags(aff, stem, suffix, prefix, flags):
    aff = Aff(**aff)
    dictionary = Dictionary(aff=aff)
    form = Form(stem, suffix=suffix, prefix=prefix)
    assert dictionary._affix_flags(form) == formula_to_flags(flags)

@pytest.mark.parametrize(
    ({}, 'cat', None, ''),
    ({onlyincompound='O'}, 'cat', None, '!O'), # found form should not marked as "onlyincompound"
)
def test_compound_flags(aff, stem, compoundpos):
    aff = Aff(**aff)
    dictionary = Dictionary(aff=aff)
    assert dictionary._compound_flags(stem, compoundpos) == formula_to_flags(flags)
