from ..constants import TransferStatus
from .handler_factory import HandlerFactory
from .tm_utils import TransferHandler, Models
import threading
import time
import os
import traceback
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter
from girder.models.model_base import ValidationException
from girder import logger


class TransferThread(threading.Thread):
    def __init__(self, itemId, transferHandler):
        threading.Thread.__init__(self, name='TransferThread[' + str(itemId) + ']')
        self.daemon = True
        self.itemId = itemId
        self.transferHandler = transferHandler

    def run(self):
        try:
            self.transferHandler.run()
        except Exception:
            traceback.print_exc()


class GirderDownloadTransferHandler(TransferHandler):

    def __init__(self, transferId, itemId, psPath):
        TransferHandler.__init__(self, transferId, itemId, psPath)

    def transfer(self):
        file = self._getFileFromItem()
        Models.transferModel.setStatus(self.transferId, TransferStatus.TRANSFERRING,
                                       size=self.flen, transferred=0, setTransferStartTime=True)
        stream = Models.fileModel.download(file, headers=False)

        try:
            os.makedirs(os.path.dirname(self.psPath))
        except OSError:
            # Right. So checking if the directory exists and then creating it is
            # prone to failure in concurrent environments. There should be a
            # function that ensures that the directory exists without failing if
            # it does. Good job, python!
            pass
        with open(self.psPath, 'wb') as outf:
            self.transferBytes(outf, stream)

    def transferBytes(self, outf, stream):
        crt = 0
        for chunk in stream():
            outf.write(chunk)
            crt = crt + len(chunk)
            self.updateTransferProgress(self.flen, crt)


class SlowGirderDownloadTransferHandler(GirderDownloadTransferHandler):
    DELAY = 1

    def __init__(self, transferId, itemId, psPath):
        GirderDownloadTransferHandler.__init__(self, transferId, itemId, psPath)

    def transferBytes(self, outf, stream):
        crt = 0
        for chunk in stream():
            outf.write(chunk)
            crt = crt + len(chunk)
            self.updateTransferProgress(self.flen, crt)
            if SlowGirderDownloadTransferHandler.DELAY > 0:
                time.sleep(SlowGirderDownloadTransferHandler.DELAY)


class TransferManager:
    def __init__(self, settings, pathMapper):
        self.settings = settings
        self.pathMapper = pathMapper
        self.handlerFactory = HandlerFactory()

    def restartInterruptedTransfers(self):
        # transfers and item.dm.transferInProgress are not atomically
        # set, so use both to figure out what needs to be re-started
        activeTransfersFromItem = Models.lockModel.listDownloadingItems()
        activeTransfers = Models.transferModel.listAll()

        ids = set()
        data = []

        for item in activeTransfersFromItem:
            ids.add(item['_id'])
            data.append({
                'itemId': item['_id'],
                'ownerId': item['dm']['transfer']['userId'],
                'sessionId': item['dm']['transfer']['sessionId']
            })
        for transfer in activeTransfers:
            if not transfer['itemId'] in ids:
                data.append(transfer)

        for item in data:
            print('Restarting transfer for item ' + str(item))
            try:
                user = self.getUser(item['ownerId'])
                self.startTransfer(user, item['itemId'], item['sessionId'])
            except Exception as ex:
                logger.warning('Failed to strart transfer for itemId %s. Reason: %s'
                               % (item['itemId'], str(ex)))

    def getUser(self, userId):
        return Models.userModel.load(userId, force=True)

    def startTransfer(self, user, itemId, sessionId):
        pass

    def transferCompleted(self, itemId):
        pass


class SimpleTransferManager(TransferManager):
    def __init__(self, settings, pathMapper):
        TransferManager.__init__(self, settings, pathMapper)
        self.restartInterruptedTransfers()

    def startTransfer(self, user, itemId, sessionId):
        # add transfer to transfer DB and initiate actual transfer
        transfer = Models.transferModel.createTransfer(user, itemId, sessionId)
        self.actualStartTransfer(user, transfer['_id'], itemId)

    def actualStartTransfer(self, user, transferId, itemId):
        transferHandler = self.getTransferHandler(transferId, itemId, user)
        transferThread = TransferThread(itemId, transferHandler)
        transferThread.start()

    def getTransferHandler(self, transferId, itemId, user):
        item = Models.itemModel.load(itemId, force=True)
        psPath = self.pathMapper.getPSPath(itemId)
        files = list(Models.itemModel.childFiles(item=item))
        if len(files) != 1:
            raise Exception(
                'Wrong number of files for item ' + str(item['_id']) + ': ' + str(len(files)))
        file = Models.fileModel.load(files[0]['_id'], force=True)

        url = None
        if 'linkUrl' in file:
            url = file['linkUrl']
        elif 'imported' in file:
            url = file['path']
        elif 'assetstoreId' in file:
            try:
                store = \
                    ModelImporter.model('assetstore').load(file['assetstoreId'])
                adapter = assetstore_utilities.getAssetstoreAdapter(store)
                url = adapter.fullPath(file)
            except (AttributeError, ValidationException):
                pass
        if url:
            try:
                file['size']
            except KeyError:
                raise ValueError('File {} must have a size attribute.'.format(str(file['_id'])))
            return self.handlerFactory.getURLTransferHandler(url, transferId, itemId, psPath, user)
        else:
            return GirderDownloadTransferHandler(transferId, itemId, psPath)


class DelayingSimpleTransferManager(SimpleTransferManager):
    def __init__(self, settings, pathMapper):
        SimpleTransferManager.__init__(self, settings, pathMapper)

    def getTransferHandler(self, transferId, itemId):
        return SlowGirderDownloadTransferHandler(transferId, itemId,
                                                 self.pathMapper.getPSPath(itemId))
