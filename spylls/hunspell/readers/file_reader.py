"""
.. autoclass:: BaseReader
    :members:

.. autoclass:: FileReader
.. autoclass:: ZipReader
"""

import io
import zipfile


class BaseReader:
    """
    Common base for :class:`FileReader` and :class:`ZipReader`. In fact, it is a very thin wrapper
    around ``IO``-alike object, to read it line by line and:

    * strip lines transparently
    * ignore BOM (byte-order mark) at the beginning
    * yield line with its number (1-based)
    * support encoding change on the fly::

        for line in reader:
            # do something
            reader.reset_encoding('UTF-8')
            # ..continue to read from the same line

    """
    def __init__(self, obj):
        self.line_no = 0

        self.reset_io(obj)

    def reset_encoding(self, encoding):
        raise NotImplementedError

    def __iter__(self):
        return self

    def __next__(self):
        return self.iter.__next__()

    def readlines(self):
        ln = self.io.readline()
        while ln != '':
            self.line_no += 1
            if self.line_no == 1 and ln.startswith("\xef\xbb\xbf"):
                ln = ln.replace("\xef\xbb\xbf", '')
            yield (self.line_no, ln.strip())
            ln = self.io.readline()

    def reset_io(self, obj):
        self.io = obj
        self.iter = filter(lambda l: l[1] != '', self.readlines())

        for _ in range(self.line_no):
            self.io.readline()


class FileReader(BaseReader):
    """
    Reader implementation for simple filesystem file.
    """

    def __init__(self, path, encoding='Windows-1252'):
        self.path = path
        super().__init__(self._open(path, encoding))

    def reset_encoding(self, encoding):
        self.reset_io(self._open(self.path, encoding))

    def _open(self, path, encoding):  # pylint: disable=no-self-use
        # errors='surrogateescape', because at least hu_HU dictionary of LibreOffice uses invalid
        # in UTF-8 single-bytes as suffix flags
        return open(path, 'r', encoding=encoding, errors='surrogateescape')


class ZipReader(BaseReader):
    """
    Reader implementation for file inside zip archive.
    """

    def __init__(self, zip_obj, encoding='Windows-1252'):
        self.zipfile = (zip_obj._fileobj._file.name, zip_obj.name)
        super().__init__(self._open(zip_obj, encoding))

    def reset_encoding(self, encoding):
        zipname, path = self.zipfile
        # FIXME: Like, really?..
        self.reset_io(self._open(zipfile.ZipFile(zipname).open(path), encoding))

    def _open(self, zip_obj, encoding):  # pylint: disable=no-self-use
        return io.TextIOWrapper(zip_obj, encoding=encoding, errors='surrogateescape')
