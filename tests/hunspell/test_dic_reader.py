from spyll.hunspell.data import dic as d
from spyll.hunspell.readers import DicReader

def test_load():
  dic = DicReader('tests/fixtures/simple.dic')()
  assert dic.words == [
    d.Word(stem='cat', flags=set()),
    d.Word(stem='dog', flags={'S', 'M'})
  ]

def test_encoding():
  dic = DicReader(
    'tests/fixtures/windows-1251.dic',
    encoding='Windows-1251'
  )()
  assert dic.words == [
    d.Word(stem='кот', flags={'S', 'M'})
  ]

def test_flag_format():
  dic = DicReader(
    'tests/fixtures/long_flags.dic',
    flag_format='long'
  )()
  assert dic.words == [
    d.Word(stem='cat', flags=set()),
    d.Word(stem='dog', flags={'So', 'Mx'})
  ]

# def test_with_number():
#   words = DicReader('tests/fixtures/with_word_count.dic', Context()).read()
#   assert words == [
#     {'stem': 'cat', 'flags': []},
#     {'stem': 'dog', 'flags': ['S', 'M']}
#   ]

# def test_with_morphology():
#   pass
