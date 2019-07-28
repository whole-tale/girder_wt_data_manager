from girder.utility.model_importer import ModelImporter


class Models:
    itemModel = ModelImporter.model('item')
    fileModel = ModelImporter.model('file')
    userModel = ModelImporter.model('user')
    transferModel = ModelImporter.model('transfer', 'wt_data_manager')
    lockModel = ModelImporter.model('lock', 'wt_data_manager')


class TransferHandler:
    TRANSFER_UPDATE_MIN_CHUNK_SIZE = 1024 * 1024
    TRANSFER_UPDATE_MIN_FRACTIONAL_CHUNK_SIZE = 0.001

    def __init__(self, transferId, itemId, psPath, user, transferManager):
        self.transferId = transferId
        self.itemId = itemId
        self.psPath = psPath
        self.user = user
        self.transferManager = transferManager
        self.flen = 0
        self.item = Models.itemModel.load(self.itemId, force=True)
        self.lastTransferred = 0

    def _getFileFromItem(self):
        files = list(Models.itemModel.childFiles(item=self.item))
        if len(files) != 1:
            raise Exception(
                'Wrong number of files for item ' + str(self.item['_id']) + ': ' + str(len(files)))
        return Models.fileModel.load(files[0]['_id'], force=True)

    def run(self):
        self.transfer()

    def getTransferredByteCount(self):
        return self.flen

    def getItemId(self):
        return self.itemId

    def getPhysicalPath(self):
        return self.psPath

    def transfer(self):
        pass

    def updateTransferProgress(self, size, transferred):
        # to avoid too many db requests, update only on:
        # - TRANSFER_UPDATE_MIN_CHUNK_SIZE AND
        # - TRANSFER_UPDATE_MIN_FRACTIONAL_CHUNK_SIZE transferred
        #   (less would not be visible on a progress bar shorted than 1000px)
        delta = transferred - self.lastTransferred
        if delta >= TransferHandler.TRANSFER_UPDATE_MIN_CHUNK_SIZE and \
                delta >= size * TransferHandler.TRANSFER_UPDATE_MIN_FRACTIONAL_CHUNK_SIZE:

            self.transferManager.transferProgress(self.transferId, total=size, current=transferred)
            self.lastTransferred = transferred

    def isManaged(self):
        """
        Returns True if this handler uses a managed transfer service. In principle,
        a managed transfer service takes care of error handling (e.g., retries, backoff, etc.).
        In the event that the infrastructure also implements error handling, this
        flag can be used to indicate that error handling should be left to the transfer
        service.
        """
        return False

class TransferException(Exception):
    def __init__(self, message=None, cause=None, fatal=True):
        super().__init__()
        self.message = message
        self.cause = cause
        self.fatal = fatal

    def getMessage(self):
        return self.message

    def getCause(self):
        return self.cause

    def isFatal(self):
        return self.fatal