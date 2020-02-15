from spyll.hunspell.algo import compounder as cpd


def test_decompose():
    compounder = cpd.Compounder(min_length=3, max_words=2)

    assert compounder('cats') == []
    assert compounder('catastrophe') == [
        [cpd.Part('cat', cpd.Pos.BEGIN), cpd.Part('astrophe', cpd.Pos.END)],
        [cpd.Part('cata', cpd.Pos.BEGIN), cpd.Part('strophe', cpd.Pos.END)],
        [cpd.Part('catas', cpd.Pos.BEGIN), cpd.Part('trophe', cpd.Pos.END)],
        [cpd.Part('catast', cpd.Pos.BEGIN), cpd.Part('rophe', cpd.Pos.END)],
        [cpd.Part('catastr', cpd.Pos.BEGIN), cpd.Part('ophe', cpd.Pos.END)],
        [cpd.Part('catastro', cpd.Pos.BEGIN), cpd.Part('phe', cpd.Pos.END)],
    ]

    compounder = cpd.Compounder(min_length=3, max_words=3)
    assert compounder('catastrophe') == [
        [cpd.Part('cat', cpd.Pos.BEGIN), cpd.Part('astrophe', cpd.Pos.END)],
        [cpd.Part('cat', cpd.Pos.BEGIN), cpd.Part('ast', cpd.Pos.MIDDLE), cpd.Part('rophe', cpd.Pos.END)],
        [cpd.Part('cat', cpd.Pos.BEGIN), cpd.Part('astr', cpd.Pos.MIDDLE), cpd.Part('ophe', cpd.Pos.END)],
        [cpd.Part('cat', cpd.Pos.BEGIN), cpd.Part('astro', cpd.Pos.MIDDLE), cpd.Part('phe', cpd.Pos.END)],
        [cpd.Part('cata', cpd.Pos.BEGIN), cpd.Part('strophe', cpd.Pos.END)],
        [cpd.Part('cata', cpd.Pos.BEGIN), cpd.Part('str', cpd.Pos.MIDDLE), cpd.Part('ophe', cpd.Pos.END)],
        [cpd.Part('cata', cpd.Pos.BEGIN), cpd.Part('stro', cpd.Pos.MIDDLE), cpd.Part('phe', cpd.Pos.END)],
        [cpd.Part('catas', cpd.Pos.BEGIN), cpd.Part('trophe', cpd.Pos.END)],
        [cpd.Part('catas', cpd.Pos.BEGIN), cpd.Part('tro', cpd.Pos.MIDDLE), cpd.Part('phe', cpd.Pos.END)],
        [cpd.Part('catast', cpd.Pos.BEGIN), cpd.Part('rophe', cpd.Pos.END)],
        [cpd.Part('catastr', cpd.Pos.BEGIN), cpd.Part('ophe', cpd.Pos.END)],
        [cpd.Part('catastro', cpd.Pos.BEGIN), cpd.Part('phe', cpd.Pos.END)],
    ]
