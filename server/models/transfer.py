from girder.models.model_base import AccessControlledModel
from girder.utility.model_importer import ModelImporter
from girder.utility import path as path_util
from girder.constants import AccessType
from ..constants import TransferStatus
from bson import objectid
import datetime


class Transfer(AccessControlledModel):
    OLD_TRANSFER_LIMIT = datetime.timedelta(minutes=1)

    def initialize(self):
        self.name = 'transfer'
        self.exposeFields(level=AccessType.READ,
                          fields={'_id', 'ownerId', 'sessionId', 'itemId', 'status', 'error',
                                  'size', 'transferred', 'path', 'startTime', 'endTime'})
        self.itemModel = ModelImporter.model('item')

    def validate(self, transfer):
        return transfer

    def createTransfer(self, user, itemId, sessionId):
        existing = self.findOne(query={'itemId': itemId, 'ownerId': user['_id'],
                                       'sessionId': sessionId})

        if existing is not None:
            transferId = existing['_id']
        else:
            transferId = objectid.ObjectId()

        try:
            pathFromRoot = self.getPathFromRoot(user, itemId)
        except KeyError as ex:
            # item does not exist any more, so delete existing transfer
            if existing is not None:
                self.remove(existing)
            raise ex
        transfer = {
            '_id': transferId,
            'ownerId': user['_id'],
            'sessionId': sessionId,
            'itemId': itemId,
            'status': TransferStatus.QUEUED,
            'error': None,
            'size': 0,
            'transferred': 0,
            'path': pathFromRoot
        }

        self.setUserAccess(transfer, user=user, level=AccessType.ADMIN)
        transfer = self.save(transfer)

        return transfer

    def getPathFromRoot(self, user, itemId):
        item = self.itemModel.load(itemId, user=user, level=AccessType.READ)
        return path_util.getResourcePath('item', item, user=user)

    def setStatus(self, transferId, status, error=None, size=0, transferred=0,
                  setTransferStartTime=False, setTransferEndTime=False):

        update = {
            '$set': {
                'status': status,
                'error': error,
                'size': size,
                'transferred': transferred
            }
        }

        if setTransferStartTime or setTransferEndTime:
            update['$currentDate'] = {}

        if setTransferStartTime:
            update['$currentDate']['startTime'] = {'$type': 'timestamp'}

        if setTransferEndTime:
            update['$currentDate']['endTime'] = {'$type': 'timestamp'}

        self.update(
            query={'_id': transferId},
            update=update
        )

    def list(self, user, sessionId=None, discardOld=True):
        if sessionId is None:
            return self.listAllForUser(user, discardOld=discardOld)
        else:
            return self.listAllForSession(user, sessionId, discardOld=discardOld)

    def listAll(self, discardOld=True):
        query = self.getTimeConstraintQuery(discardOld)
        return self.find(query)

    def listAllForUser(self, user, discardOld=True):
        query = self.getTimeConstraintQuery(discardOld)
        query['ownerId'] = user['_id']
        return self.find(query)

    def listAllForSession(self, user, sessionId, discardOld=True):
        query = self.getTimeConstraintQuery(discardOld)
        query['ownerId'] = user['_id']
        query['sessionId'] = sessionId
        return self.find(query)

    def getTimeConstraintQuery(self, discardOld):
        if discardOld:
            return {
                '$or': [
                    {
                        'endTime': {
                            '$exists': False
                        }
                    },
                    {
                        'endTime': {
                            '$gte': datetime.datetime.utcnow() - Transfer.OLD_TRANSFER_LIMIT
                        }
                    }
                ]
            }
        else:
            return {}
