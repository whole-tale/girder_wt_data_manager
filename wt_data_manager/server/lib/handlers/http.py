import urllib2
from common import FileLikeUrlTransferHandler

class Http(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath)

    def openInputStream(self):
        return urllib2.urlopen(self.url)
