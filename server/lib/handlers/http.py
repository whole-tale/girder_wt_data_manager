import requests
from .common import FileLikeUrlTransferHandler


class Http(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user,
                                            transferManager)

    def openInputStream(self):
        return requests.get(self.url, stream=True, headers=self.headers).raw
