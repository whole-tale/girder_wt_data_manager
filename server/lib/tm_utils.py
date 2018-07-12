from girder.utility.model_importer import ModelImporter
from girder import events
from ..constants import TransferStatus
import traceback


class Models:
    itemModel = ModelImporter.model('item')
    fileModel = ModelImporter.model('file')
    userModel = ModelImporter.model('user')
    transferModel = ModelImporter.model('transfer', 'wt_data_manager')
    lockModel = ModelImporter.model('lock', 'wt_data_manager')


class TransferHandler:
    TRANSFER_UPDATE_MIN_CHUNK_SIZE = 1024 * 1024
    TRANSFER_UPDATE_MIN_FRACTIONAL_CHUNK_SIZE = 0.001

    def __init__(self, transferId, itemId, psPath, user):
        self.transferId = transferId
        self.itemId = itemId
        self.psPath = psPath
        self.user = user
        self.flen = 0
        self.item = Models.itemModel.load(self.itemId, force=True)
        self.lastTransferred = 0

    def _getFileFromItem(self):
        files = list(Models.itemModel.childFiles(item=self.item))
        if len(files) != 1:
            raise Exception('Wrong number of files for item ' + str(self.item['_id']) +
                            ': ' + str(len(files)))
        return Models.fileModel.load(files[0]['_id'], force=True)

    def run(self):
        try:
            Models.transferModel.setStatus(self.transferId,
                                           TransferStatus.INITIALIZING)
            self.transfer()
            Models.transferModel.setStatus(self.transferId, TransferStatus.DONE, size=self.flen,
                                           transferred=self.flen, setTransferEndTime=True)
            self.transferDone()
        except Exception as ex:
            self._failTransfer(ex)

    def _failTransfer(self, ex):
        traceback.print_exc()
        Models.transferModel.setStatus(self.transferId, TransferStatus.FAILED,
                                       error=str(ex), setTransferEndTime=True)

    def transfer(self):
        pass

    def transferDone(self):
        events.trigger('dm.fileDownloaded', info={'itemId': self.itemId, 'psPath': self.psPath})

    def updateTransferProgress(self, size, transferred):
        # to avoid too many db requests, update only on:
        # - TRANSFER_UPDATE_MIN_CHUNK_SIZE AND
        # - TRANSFER_UPDATE_MIN_FRACTIONAL_CHUNK_SIZE transferred
        #   (less would not be visible on a progress bar shorted than 1000px)
        delta = transferred - self.lastTransferred
        if delta >= TransferHandler.TRANSFER_UPDATE_MIN_CHUNK_SIZE and \
                delta >= size * TransferHandler.TRANSFER_UPDATE_MIN_FRACTIONAL_CHUNK_SIZE:

            Models.transferModel.setStatus(self.transferId, TransferStatus.TRANSFERRING, size=size,
                                           transferred=transferred)
            self.lastTransferred = transferred
