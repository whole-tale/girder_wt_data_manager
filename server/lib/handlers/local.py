from six.moves.urllib.parse import urlparse
from .common import FileLikeUrlTransferHandler


class Local(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath, user):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user)

    def openInputStream(self):
        parsedUrl = urlparse(self.url)
        return open(parsedUrl.path, 'rb')
