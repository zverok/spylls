import io

from spyll.hunspell.readers import FileReader

def test_lines():
  reader = FileReader('tests/fixtures/basic-utf8.txt')

  assert list(reader) == [(1, 'line'), (4, 'content')]

def test_encodings():
  reader = FileReader('tests/fixtures/basic-win1251.txt')
  assert reader.__next__() == (1, 'set Windows-1251')
  reader.reset_encoding('Windows-1251')
  assert list(reader) == [(2, 'раз'), (3, 'два')]

def test_stringio():
  strigio = io.StringIO("""line

    # empty, too
    content # comment
  """)

  reader = FileReader(strigio)

  assert list(reader) == [(1, 'line'), (4, 'content')]
