from six.moves.urllib.request import urlopen
from .common import FileLikeUrlTransferHandler


class HttpStream:
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return self

    def read(self, sz=-1):
        return self.stream.read(sz)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # dear python, do these need to be closed if not all data is read?
        return True


class Http(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath)

    def openInputStream(self):
        return HttpStream(urlopen(self.url))
