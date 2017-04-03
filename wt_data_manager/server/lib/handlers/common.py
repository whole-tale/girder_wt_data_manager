from ..transfer_manager import TransferHandler, Models, TransferStatus
import os


class UrlTransferHandler(TransferHandler):
    def __init__(self, url, transferId, itemId, psPath):
        TransferHandler.__init__(self, transferId, itemId, psPath)
        self.url = url
        self.flen = self.item['meta']['size']

    def mkdirs(self):
        try:
            os.makedirs(os.path.dirname(self.psPath))
        except OSError:
            pass


class FileLikeUrlTransferHandler(UrlTransferHandler):
    BUFSZ = 32768

    def __init__(self, url, transferId, itemId, psPath):
        UrlTransferHandler.__init__(self, url, transferId, itemId, psPath)

    def transfer(self):
        Models.transferModel.setStatus(self.transferId, TransferStatus.TRANSFERRING,
                                       size=self.flen, transferred=0, setTransferStartTime=True)

        self.mkdirs()
        with open(self.psPath, 'w') as outf, self.openInputStream() as inf:
            self.transferBytes(outf, inf)

    def openInputStream(self):
        raise NotImplementedError()

    def transferBytes(self, outf, inf):
        crt = 0

        while True:
            buf = inf.read(FileLikeUrlTransferHandler.BUFSZ)
            if buf == '':
                break
            outf.write(buf)
            crt = crt + len(buf)
            self.updateTransferProgress(self.flen, crt)
