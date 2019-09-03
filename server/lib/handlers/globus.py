from ..tm_utils import TransferHandler, TransferException
from girder.plugins.globus_handler.server import Server
from girder.plugins.globus_handler.clients import Clients
from threading import Lock
from globus_sdk import TransferData
from girder.utility.model_importer import ModelImporter
from girder import logger
from urllib.parse import urlparse
import uuid
import time
import shutil
import os


class Globus(TransferHandler):
    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        TransferHandler.__init__(self, transferId, itemId, psPath, user, transferManager)
        self.url = url
        self.server = None
        self.serverLock = Lock()
        self.clients = Clients()

    def isManaged(self):
        return True

    def transfer(self):
        # this isn't very scalable and there isn't much wisdom in wasting a thread on a transfer
        # that is directed by another machine, but we waste an entire process or more on the
        # gridftp server processes anyway, so this may not quite be the bottleneck
        self._maybeStartServer()
        userEndpointId = self.server.getUserEndpointId(self.user)
        tc = self.clients.getUserTransferClient(self.user)

        tmpName = str(uuid.uuid4())
        transfer = TransferData(tc, self._getSourceEndpointId(), userEndpointId,
                                label=str(self.transferId))
        transfer['notify_on_succeeded'] = False
        transfer['notify_on_failed'] = False
        transfer['notify_on_inactive'] = False
        transfer.add_item(self._getSourcePath(), tmpName)
        res = tc.submit_transfer(transfer)
        if res['code'] != 'Accepted':
            raise Exception('Transfer submission failed: %s - %s' % (res.code, res.message))
        taskId = res['task_id']
        self._updateTransfer(tmpName, taskId)
        while True:
            task = tc.get_task(taskId)
            status = task['status']
            if status == 'ACTIVE':
                # update bytes
                self.transferManager.transferProgress(self.transferId, -1,
                                                      task['bytes_transferred'])
            elif status == 'INACTIVE':
                # credential expiration
                # TODO: deal with this properly or ensure it does not happen
                msg = 'Credential expired for Globus task %s, transfer %s.' % (taskId,
                                                                               self.transferId)
                logger.warn(msg)
                raise TransferException(message=msg, fatal=True)
            elif status == 'SUCCEEDED':
                dir = os.path.dirname(self.psPath)
                try:
                    os.makedirs(dir)
                except OSError:
                    if not os.path.exists(dir):
                        raise TransferException(message='Could not create transfer destination '
                                                        'directory: %s' % dir, fatal=True)
                shutil.move('%s/%s' % (self.server.getUserDir(self.user), tmpName), self.psPath)
                return
            elif status == 'FAILED':
                if task['fatal_error']:
                    raise TransferException(
                        message='Globus transfer %s failed: %s' %
                        (self.transferId, task['fatal_error']['description']),
                        fatal=True)
                else:
                    raise Exception(message='Globus transfer %s failed for unknown reasons' %
                                    self.transferId, fatal=False)
            else:
                raise Exception(messsage='Unknown globus task status %s for transfer %s' %
                                (status, self.transferId), fatal=False)
            time.sleep(10)

    def _getSourceEndpointId(self):
        up = urlparse(self.url)
        return up.netloc

    def _getSourcePath(self):
        up = urlparse(self.url)
        return up.path

    def _getDestPath(self, tmpName):
        return '%s/%s' % (self.user['login'], tmpName)

    def _updateTransfer(self, tmpName, taskId):
        transferModel = ModelImporter.model('transfer', 'wt_data_manager')
        ti = transferModel.load(self.transferId, force=True)
        ti['tmpName'] = tmpName
        ti['globusTaskId'] = taskId
        transferModel.save(ti)

    def _maybeStartServer(self):
        with self.serverLock:
            if self.server is None:
                self.server = Server(self.clients)
                self.server.start()
