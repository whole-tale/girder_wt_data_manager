#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from bson import objectid
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter
from girder.models.model_base import AccessControlledModel, AccessException
from girder import events


class Session(AccessControlledModel):
    def initialize(self):
        self.name = 'session'
        self.exposeFields(
            level=AccessType.READ,
            fields={'_id', 'status', 'ownerId', 'dataSet', 'error', 'seq', 'taleId'})
        self.folderModel = ModelImporter.model('folder')
        self.itemModel = ModelImporter.model('item')
        self.lockModel = ModelImporter.model('lock', 'wt_data_manager')

    def validate(self, session):
        return session

    def list(self, user, limit=0, offset=0, sort=None):
        """
        List a page of containers for a given user.

        :param user: The user who owns the job.
        :type user: dict or None
        :param limit: The page limit.
        :param offset: The page offset
        :param sort: The sort field.
        """
        userId = user['_id'] if user else None
        cursor = self.find({'ownerId': userId}, sort=sort)

        for r in self.filterResultsByPermission(cursor=cursor, user=user, level=AccessType.READ,
                                                limit=limit, offset=offset):
            yield r

    def createSession(self, user, dataSet=None, tale=None):
        """
        Create a new session.

        :param user: The user creating the session.
        :type user: dict or None
        :param dataSet: The initial dataSet associated with this session. The dataSet is a list
         of dictionaries with two keys: 'itemId', and 'mountPath'
        :type dataSet: list
        :param tale: If a tale is provided, use dataSet associated with it to initialize
         a session.
        :type tale: dict or None
        """

        session = {
            'ownerId': user['_id'],
            'seq': 0,
            'taleId': None
        }

        if tale:
            session['dataSet'] = tale['involatileData']
            session['taleId'] = tale['_id']
        else:
            session['dataSet'] = dataSet

        session = self.setUserAccess(session, user=user, level=AccessType.ADMIN, save=True)
        # TODO: is the custom event really necessary? save in here ^^ already triggers
        #  'model.session.save', with info=session
        events.trigger('dm.sessionCreated', info=session)

        return session

    def modifySession(self, user, session, dataSet):
        """
        Modify an existing session.

        :param user: Must be the owner of the session
        :type user: dict or None
        :param session: The session that is being modified
        :type session: dict
        :param dataSet: The new dataSet to associate with this session. See createSession for
         details
        :type dataSet: list
        :return:
        """

        self.checkOwnership(user, session)
        self.update(
            query={'_id': session['_id']},
            update={
                '$inc': {'seq': 1},
                '$set': {'dataSet': dataSet}
            },
            multi=False)
        session = self.load(session['_id'], user=user)
        events.trigger('dm.sessionModified', info=session)
        return session

    def loadObjects(self, dataSet):
        for entry in dataSet:
            if 'type' in entry:
                continue
            folder = self.folderModel.load(entry['itemId'], force=True)
            if folder is not None:
                entry['type'] = 'folder'
                entry['obj'] = folder
            else:
                entry['type'] = 'item'
                entry['obj'] = self.itemModel.load(entry['itemId'], force=True)

    def checkOwnership(self, user, session):
        if user['admin']:
            # admin owns everything
            return
        if 'ownerId' in session:
            ownerId = session['ownerId']
        else:
            ownerId = session['userId']
        if ownerId != user['_id']:
            raise AccessException('Current user is not the session owner')

    def containsItem(self, sessionId, objectId, user):
        """
        Check whether an item is accessible when the dataSet of this session is mounted
        in a filesystem. This means that either this item or one of its ancestors is in
        the dataSet
        :param sessionId: The session in which to check the presence of the item
        :param itemId: The item to find
        :param user: The user owning the session
        :return:
        """
        if isinstance(objectId, str):
            objectId = objectid.ObjectId(objectId)
        session = self.load(sessionId, level=AccessType.READ, user=user)
        idSet = set()
        for entry in session['dataSet']:
            idSet.add(objectid.ObjectId(entry['itemId']))

        return self._containsItemOrAncestor(idSet, objectId)

    def _containsItemOrAncestor(self, idSet, objectId):
        if objectId is None:
            return False
        if objectId in idSet:
            return True
        return self._containsItemOrAncestor(idSet, self._getParentId(objectId))

    def _getParentId(self, objectId):
        """
        Returns the id of the parent folder of a Girder folder or item. Returns None
        if the folder has no parent. This does not handle collections. If a folder
        is a child of a collection, it would be considered without a parent. This
        reflects the fact that we can't properly mount collections at this point.
        :param objectId: The id of the folder/item to get the parent for
        :return:
        """

        folder = self.folderModel.findOne(query={'_id': objectId}, fields=['parentId'])
        if folder is not None:
            return folder['parentId']
        item = self.itemModel.findOne(query={'_id': objectId}, fields=['folderId'])
        if item is not None:
            return item['folderId']

        return None

    def deleteSession(self, user, session):
        self.checkOwnership(user, session)
        self.remove(session)
        events.trigger('dm.sessionDeleted', info=session)

    def getObject(self, user, session, path, children):
        self.checkOwnership(user, session)

        (tail, rootContainer) = self.findRootContainer(session, path)
        crtObj = rootContainer

        if tail is not None:
            pathEls = self.splitPath(tail)
            for item in pathEls:
                crtObj = self.findObjectInFolder(crtObj, item)

        if children:
            return {
                'object': crtObj,
                'children': self.listChildren(crtObj)
            }
        else:
            return {
                'object': crtObj
            }

    def findRootContainer(self, session, path):
        for obj in session['dataSet']:
            rootPath = obj['mountPath']
            if path == rootPath:
                return (None, self.loadObject(str(obj['itemId'])))
            if rootPath[-1] != '/':
                # add a slash at the end to avoid situations like
                # rootPath=/name being matched for path=/nameAndStuff/...
                rootPath = rootPath + '/'
            if path.startswith(rootPath):
                return (path[len(rootPath):], self.loadObject(str(obj['itemId'])))
        raise LookupError('No such object: ' + path)

    def loadObject(self, id):
        item = self.folderModel.load(id, level=AccessType.READ)
        if item is not None:
            item['type'] = 'folder'
            return item
        else:
            item = self.itemModel.load(id, level=AccessType.READ)
            if item is not None:
                item['type'] = 'file'
                return item
        raise LookupError("No such object: " + id)

    def listChildren(self, item):
        children = list(self.folderModel.childFolders(item, 'folder'))
        children.extend(self.folderModel.childItems(item))
        return children

    def findObjectInFolder(self, container, name):
        parentId = container['_id']

        item = self.folderModel.findOne(query={'parentId': parentId, 'name': name},
                                        level=AccessType.READ)
        if item is not None:
            item['type'] = 'folder'
            return item
        item = self.itemModel.findOne(query={'folderId': parentId, 'name': name},
                                      level=AccessType.READ)
        if item is not None:
            item['type'] = 'file'
            return item
        raise LookupError('No such object: ' + name)

    def splitPath(self, path):
        current_path = []
        while path != '' and path != '/':
            (path, tail) = os.path.split(path)
            current_path.insert(0, tail)
        return current_path
