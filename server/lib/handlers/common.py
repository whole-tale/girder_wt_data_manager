from ..tm_utils import TransferHandler
import os

from girder.plugins.wholetale.lib import Verificators


class UrlTransferHandler(TransferHandler):
    _headers = None

    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        TransferHandler.__init__(self, transferId, itemId, psPath, user, transferManager)
        self.url = url
        self.flen = self._getFileFromItem()['size']

        try:
            verificator = Verificators[self.item["meta"]["provider"].lower()]
            self._headers = verificator(user=user, url=url).headers
        except KeyError:
            pass

    @property
    def headers(self):
        if self._headers:
            return self._headers
        return {}

    def mkdirs(self):
        try:
            os.makedirs(os.path.dirname(self.psPath))
        except OSError:
            pass


class FileLikeUrlTransferHandler(UrlTransferHandler):
    BUFSZ = 32768

    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        UrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user, transferManager)

    def transfer(self):
        self.transferManager.transferProgress(self.transferId, self.flen, 0)
        self.mkdirs()
        with open(self.psPath, 'wb') as outf, self.openInputStream() as inf:
            self.transferBytes(outf, inf)

    def openInputStream(self):
        raise NotImplementedError()

    def transferBytes(self, outf, inf):
        crt = 0
        while True:
            buf = inf.read(FileLikeUrlTransferHandler.BUFSZ)
            if not buf:
                break
            outf.write(buf)
            crt = crt + len(buf)
            self.updateTransferProgress(self.flen, crt)
