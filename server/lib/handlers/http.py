from six.moves.urllib.request import urlopen, Request
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
    def __init__(self, url, transferId, itemId, psPath, user):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user)

    def openInputStream(self):
        if self.item['meta']['provider'] == "DesignSafe" or self.item['meta']['provider'] == "CyVerse":
            headers = {"Authorization": "Bearer %s" % self.user['agaveAccessToken']}
            request = Request(self.url, None, headers=headers)
            return HttpStream(urlopen(request))
        return HttpStream(urlopen(self.url))
