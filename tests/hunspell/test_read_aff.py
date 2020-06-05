import io

# from spyll.hunspell.data import aff
from spyll.hunspell.readers.file_reader import FileReader
from spyll.hunspell.readers import aff

def test_directives():
    def directive(line, next_lines='', **kwarg):
        source = FileReader(io.StringIO(next_lines))
        context = aff.Context(**kwarg)
        return aff.read_directive(source, line, context=context)

    assert directive('REP 5',
        """
        REP ^Ca$ Ça
        REP ^l l'
        REP ^d d'
        REP ^n n'
        REP ^s s'
        """) == ('REP', [
            ("^Ca$", "Ça"),
            ("^l", "l'"),
            ("^d", "d'"),
            ("^n", "n'"),
            ("^s", "s'")
        ])

    assert directive('MAP 3',
        """
        MAP uúü
        MAP öóo
        MAP ß(ss)
        """) == ('MAP', [
            ['u', 'ú', 'ü'],
            ['ö', 'ó', 'o'],
            ['ß', 'ss']
        ])

    assert directive('PFX A Y 1',
        'PFX A 0 re .', ignore='aeiou')[1][0].add == 'r'

def test_long_flags():
    data, _ = aff.read_aff(io.StringIO("""
        FLAG long

        SFX zx Y 1
        SFX zx 0 s/g?1G09 .

        NOSUGGEST 1G

        AF 2
        AF AB
        AF BC
        """))

    assert data.SFX['zx'][0].flag == 'zx'
    assert data.SFX['zx'][0].flags == {'g?', '1G', '09'}

    assert data.NOSUGGEST == '1G'

    assert data.AF == {'1': {'AB'}, '2': {'BC'}}

def test_numeric_flags():
    data, _ = aff.read_aff(io.StringIO("""
        FLAG num

        SFX 999 Y 1
        SFX 999 0 s/214,216,54321 .

        NOSUGGEST 348
        """))

    assert data.SFX['999'][0].flag == '999'
    assert data.SFX['999'][0].flags == {'214', '216', '54321'}

    assert data.NOSUGGEST == '348'

def test_utf_flags():
    data, _ = aff.read_aff(io.StringIO("""
        FLAG UTF-8

        SFX A Y 1
        SFX A 0 s/ÖüÜ .

        NOSUGGEST ю
        """))

    assert data.SFX['A'][0].flag == 'A'
    assert data.SFX['A'][0].flags == {'Ö', 'ü', 'Ü'}

    assert data.NOSUGGEST == 'ю'

def test_flag_aliases():
    data, _ = aff.read_aff(io.StringIO("""
        AF 2
        AF AB
        AF BC

        SFX z Y 1
        SFX z 0 s/1 .
        """))

    assert data.SFX['z'][0].flags == {'A', 'B'}
