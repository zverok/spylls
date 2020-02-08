import re
import io
import sys

class FileReader:
  def __init__(self, path_or_io, encoding='ASCII'):
    if isinstance(path_or_io, str):
      self.path = path_or_io
      self.io = open(path_or_io, 'r', encoding=encoding, errors='ignore')
    elif isinstance(path_or_io, io.TextIOBase):
      self.path = None
      self.io = path_or_io

    self.skip_lines = 0
    self.reset_encoding(encoding=encoding)

  def __iter__(self):
    return self

  def __next__(self):
    return self.iter.__next__()

  def reset_encoding(self, encoding):
    # was initialized with StringIO or something, can't reopen.
    # FIXME: Isn't there a method to reopen the stream by its variable, yet?..
    if self.path is not None:
      self.io = open(self.path, 'r', encoding=encoding, errors='ignore')

    self.iter = filter(lambda l: l[1] != '', enumerate(self.readlines(), 1))

    if self.path is not None:
      # skipping only makes sense when it was reopened
      for i in range(self.skip_lines): self.__next__()

  def readlines(self):
    ln = self.io.readline()
    while ln != '':
      self.skip_lines += 1
      yield re.sub(r'\#.+$', '', ln).strip()
      ln = self.io.readline()
