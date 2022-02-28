import hashlib
import os

from girder.constants import AccessType
from girder.models.item import Item
from girder.plugins.wholetale.lib import Verificators

from ..tm_utils import TransferHandler, TransferException


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

    def verify_checksum(self):
        item = Item().load(self.itemId, user=self.user, level=AccessType.READ)
        if (checksums := item.get("meta", {}).get("checksum")):
            alg, value = list(checksums.items())[0]  # Get just one
            h = hashlib.new(alg.lower())

            with open(self.psPath, "rb") as fp:
                while True:
                    data = fp.read(2**22)  # 4MB chunks
                    if not data:
                        break
                    h.update(data)
            if h.hexdigest() != value:
                os.remove(self.psPath)
                raise TransferException(
                    message=f"Checksum verification failed for item:{self.itemId}",
                    fatal=True
                )


class FileLikeUrlTransferHandler(UrlTransferHandler):
    BUFSZ = 32768

    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        UrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user, transferManager)

    def transfer(self):
        self.transferManager.transferProgress(self.transferId, self.flen, 0)
        self.mkdirs()
        with open(self.psPath, 'wb') as outf, self.openInputStream() as inf:
            self.transferBytes(outf, inf)
        self.verify_checksum()

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
