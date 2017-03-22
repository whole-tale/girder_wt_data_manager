from ..models import transfer
from ..models.lock import Lock
from ..constants import TransferStatus
import threading
from girder.models import item, file, user
import time
from girder import events
import os
import traceback

class Models:
    itemModel = item.Item()
    fileModel = file.File()
    userModel = user.User()
    transferModel = transfer.Transfer()
    lockModel = Lock()

class TransferThread(threading.Thread):
    def __init__(self, itemId, transferHandler):
        threading.Thread.__init__(self, name = 'TransferThread[' + str(itemId) + ']')
        self.daemon = True
        self.itemId = itemId
        self.transferHandler = transferHandler

    def run(self):
        try:
            self.transferHandler.run()
        except Exception as ex:
            traceback.print_exc()

class TransferHandler:
    def __init__(self, transferId, itemId, psPath):
        self.transferId = transferId
        self.itemId = itemId
        self.psPath = psPath
        self.flen = 0

    def run(self):
        try:
            Models.transferModel.setStatus(self.transferId,
                TransferStatus.INITIALIZING)
            self.transfer()
            Models.transferModel.setStatus(self.transferId,
                TransferStatus.DONE, size = self.flen, transferred = self.flen, setTransferEndTime = True)
            self.transferDone()
        except Exception as ex:
            Models.transferModel.setStatus(self.transferId,
                TransferStatus.FAILED, error = ex.message, setTransferEndTime = True)
            traceback.print_exc()

    def transfer(self):
        pass

    def transferDone(self):
        events.trigger('dm.fileDownloaded', info = {'itemId': self.itemId, 'psPath': self.psPath})


class GirderDownloadTransferHandler(TransferHandler):

    def __init__(self, transferId, itemId, psPath):
        TransferHandler.__init__(self, transferId, itemId, psPath)


    def transfer(self):
        item = Models.itemModel.load(self.itemId, force = True)
        files = list(Models.itemModel.childFiles(item = item))
        if len(files) != 1:
            raise Exception('Wrong number of files for item ' + str(self.itemId) + ': ' + str(len(files)))
        fileId = files[0]['_id']
        self.flen = files[0]['size']
        Models.transferModel.setStatus(self.transferId,
            TransferStatus.TRANSFERRING, size = self.flen, transferred = 0, setTransferStartTime = True)
        file = Models.fileModel.load(fileId, force = True)
        stream = Models.fileModel.download(file, headers = False)

        try:
            os.makedirs(os.path.dirname(self.psPath))
        except OSError:
            # Right. So checking if the directory exists and then creating it is
            # prone to failure in concurrent environments. There should be a
            # function that ensures that the directory exists without failing if
            # it does. Good job, python!
            pass
        with open(self.psPath, 'w') as outf:
            self.transferBytes(outf, stream)

    def transferBytes(self, outf, stream):
        crt = 0
        for chunk in stream():
            outf.write(chunk)
            crt = crt + len(chunk)
            self.updateTransferStatus(crt)

    def updateTransferStatus(self, transferred):
        Models.transferModel.setStatus(self.transferId,
            TransferStatus.TRANSFERRING, size = self.flen, transferred = transferred)

class SlowGirderDownloadTransferHandler(GirderDownloadTransferHandler):
    DELAY = 1

    def __init__(self, transferId, itemId, psPath):
        GirderDownloadTransferHandler.__init__(self, transferId, itemId, psPath)

    def transferBytes(self, outf, stream):
        crt = 0
        for chunk in stream():
            outf.write(chunk)
            crt = crt + len(chunk)
            self.updateTransferStatus(crt)
            if SlowGirderDownloadTransferHandler.DELAY > 0:
                time.sleep(SlowGirderDownloadTransferHandler.DELAY)

class TransferManager:
    def __init__(self, pathMapper):
        self.pathMapper = pathMapper

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
            print 'Restarting transfer for item ' + str(item)
            self.startTransfer(self.getUser(item['ownerId']), item['itemId'], item['sessionId'])

    def getUser(self, userId):
        return Models.userModel.load(userId, force = True)

    def startTransfer(self, user, itemId, sessionId):
        pass

    def transferCompleted(self, itemId):
        pass


class SimpleTransferManager(TransferManager):
    def __init__(self, pathMapper):
        TransferManager.__init__(self, pathMapper)
        self.restartInterruptedTransfers()

    def startTransfer(self, user, itemId, sessionId):
        # add transfer to transfer DB and initiate actual transfer
        transfer = Models.transferModel.createTransfer(user, itemId, sessionId)
        self.actualStartTransfer(transfer['_id'], itemId)

    def actualStartTransfer(self, transferId, itemId):
        transferHandler = self.getTransferHandler(transferId, itemId)
        transferThread = TransferThread(itemId, transferHandler)
        transferThread.start()

    def getTransferHandler(self, transferId, itemId):
        return GirderDownloadTransferHandler(transferId, itemId, self.pathMapper.getPSPath(itemId))

class DelayingSimpleTransferManager(SimpleTransferManager):
    def __init__(self, pathMapper):
        SimpleTransferManager.__init__(self, pathMapper)

    def getTransferHandler(self, transferId, itemId):
        return SlowGirderDownloadTransferHandler(transferId, itemId, self.pathMapper.getPSPath(itemId))