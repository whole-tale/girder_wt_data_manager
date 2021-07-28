import requests
from .common import FileLikeUrlTransferHandler


class Http(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user,
                                            transferManager)

    def openInputStream(self):
        resp = requests.get(self.url, stream=True, headers=self.headers)
        resp.raise_for_status()  # Throw an exception in case transfer failed
        return resp.raw
