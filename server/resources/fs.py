import bson
from girder.api.rest import Resource, RestException
from girder.constants import AccessType, TokenScope
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.utility import assetstore_utilities
from girder.models.model_base import ValidationException


class FS(Resource):

    ONE_ITEM_ONE_FILE = True

    def __init__(self):
        super(FS, self).__init__()
        self.resourceName = 'fs'

    @access.user
    @describeRoute(
        Description('Returns an unfiltered item')
        .param('itemId', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Object was not found.', 400)
    )
    def getItemUnfiltered(self, itemId, params):
        user = self.getCurrentUser()
        item = self.model('item').load(itemId, level=AccessType.READ, user=user)
        return item

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('Returns an unfiltered object')
        .param('itemId', 'The ID of the object.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Object was not found.', 400)
    )
    def getRawObject(self, id, params):
        user = self.getCurrentUser()
        obj, type = self._discoverObject(id, user)
        return obj

    @access.public(scope=TokenScope.DATA_READ)
    @describeRoute(
        Description('List the content of a folder or item.')
        .param('id', 'The ID of the folder/item.', paramType='path')
        .errorResponse('ID was invalid.', 400)
        .errorResponse('Read access was denied for the object.', 403)
    )
    def getListing(self, id, params):
        user = self.getCurrentUser()
        obj, type = self._discoverObject(id, user)
        if type == 'item':
            return self.listItem(obj, params, user)
        if type == 'folder':
            return self.listFolder(obj, params, user)
        raise RestException('ID was invalid', code=400)

    def listFolder(self, folder, params, user):
        folders = list(
            self.model('folder').childFolders(parentType='folder',
                                              parent=folder, user=user))

        files = []
        for item in self.model('folder').childItems(folder=folder):
            childFiles = list(self.model('item').childFiles(item))
            nChildren = len(childFiles)
            if nChildren == 1 or (FS.ONE_ITEM_ONE_FILE and nChildren > 1):
                fileitem = childFiles[0]
                fileitem['folderId'] = folder['_id']
                if 'imported' not in fileitem and \
                        fileitem.get('assetstoreId') is not None:
                    try:
                        store = \
                            self.model('assetstore').load(fileitem['assetstoreId'])
                        adapter = assetstore_utilities.getAssetstoreAdapter(store)
                        fileitem["path"] = adapter.fullPath(fileitem)
                    except (ValidationException, AttributeError):
                        pass
                files.append(item)
            else:
                if FS.ONE_ITEM_ONE_FILE:
                    # probably some form of brokenness. Put it there to allow deletion/fixing
                    files.append(item)
                else:
                    folders.append(item)
        return {'folders': folders, 'files': files}

    def listItem(self, item, params, user):
        files = []
        for fileitem in self.model('item').childFiles(item):
            if 'imported' not in fileitem and \
                    fileitem.get('assetstoreId') is not None:
                try:
                    store = \
                        self.model('assetstore').load(fileitem['assetstoreId'])
                    adapter = assetstore_utilities.getAssetstoreAdapter(store)
                    fileitem["path"] = adapter.fullPath(fileitem)
                except (ValidationException, AttributeError):
                    pass
            files.append(fileitem)
        return {'folders': [], 'files': files}

    @access.user
    @describeRoute(
        Description('Set arbitrary property on folder/item/file')
        .param('id', 'The ID of the object.', paramType='path')
        .errorResponse('ID was invalid.', 400)
        .errorResponse('Write access was denied.', 403)
    )
    def setProperties(self, id, params):
        id = bson.ObjectId(id)
        print("set props %s" % id)
        user = self.getCurrentUser()
        obj = None
        type = None
        if 'type' in params:
            type = params['type']

        if type is None:
            obj, type = self._discoverObject(id, user, AccessType.ADMIN)
        props = self.getBodyJson()

        self.model(type).update(query={'_id': id}, update={'$set': props})

    def _discoverObject(self, id, user, access=AccessType.READ):
        for model in ['file', 'item', 'folder']:
            obj = self.model(model).load(id, level=access, user=user)
            if obj is not None:
                return obj, model
        raise RestException('ID was invalid.', code=400)
