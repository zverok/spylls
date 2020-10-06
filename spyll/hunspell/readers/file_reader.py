import re
import io
import zipfile
import copy


class FileReader:
    COMMENT_RE = re.compile(r'\#.*$')

    def __init__(self, path_or_io, encoding='Windows-1252'):
        self.zipfile = None
        self.path = None

        if isinstance(path_or_io, str):
            self.path = path_or_io
            self.io = open(path_or_io, 'r', encoding=encoding, errors='ignore')
        elif isinstance(path_or_io, io.TextIOBase):
            self.io = path_or_io
        elif isinstance(path_or_io, zipfile.ZipExtFile):
            self.zipfile = (path_or_io._fileobj._file.name, path_or_io.name)
            self.io = io.TextIOWrapper(path_or_io, encoding=encoding, errors='ignore')
        else:
            raise ValueError(f"Expected path or IO, got {type(path_or_io)}")

        self.skip_lines = 0
        self.reset_encoding(encoding=encoding)

    def __iter__(self):
        return self

    def __next__(self):
        return self.iter.__next__()

    def reset_encoding(self, encoding):
        # was initialized with StringIO or something, can't reopen.
        # FIXME: Isn't there a method to reopen the stream by its variable, yet?..
        reopened = False
        if self.path is not None:
            self.io = open(self.path, 'r', encoding=encoding, errors='ignore')
            reopened = True
        elif self.zipfile is not None:
            zipname, path = self.zipfile
            # FIXME: Like, really?..
            self.io = io.TextIOWrapper(zipfile.ZipFile(zipname).open(path), encoding=encoding, errors='ignore')
            reopened = True

        self.iter = filter(lambda l: l[1] != '', enumerate(self.readlines(), self.skip_lines+1))

        if reopened:
            for _ in range(self.skip_lines):
                self.io.readline()

    def readlines(self):
        ln = self.io.readline()
        while ln != '':
            self.skip_lines += 1 # TODO: rename to just lineno? and can be yielded instead of enumerate...
            if self.skip_lines == 1 and ln.startswith("\xef\xbb\xbf"):
                ln = ln.replace("\xef\xbb\xbf", '')
            yield self.COMMENT_RE.sub('', ln).strip()
            ln = self.io.readline()
