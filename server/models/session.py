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
        self.exposeFields(level=AccessType.READ,
                          fields={'_id', 'status', 'ownerId', 'dataSet', 'error'})
        self.folderModel = ModelImporter.model('folder')
        self.itemModel = ModelImporter.model('item')
        self.lockModel = ModelImporter.model('lock', 'wt_data_manager')
        self.objFields = ['_id', 'created', 'name', 'size', 'updated']

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

    def createSession(self, user, dataSet=None):
        """
        Create a new session.

        :param user: The user creating the job.
        :type user: dict or None
        :param dataSet: The initial dataSet associated with this session. The dataSet is a list
         of dictionaries with two keys: 'itemId', and 'mountPoint'
        :type dataSet: list
        """

        session = {
            '_id': objectid.ObjectId(),
            'ownerId': user['_id'],
            'dataSet': dataSet
        }

        self.setUserAccess(session, user=user, level=AccessType.ADMIN)

        session = self.save(session)

        events.trigger('dm.sessionCreated', info=session)

        return session

    def loadObjects(self, dataSet):
        for entry in dataSet:
            if 'type' in entry:
                continue
            folder = self.folderModel.load(entry['itemId'], force=True, fields=self.objFields)
            if folder is not None:
                entry['type'] = 'folder'
                entry['obj'] = folder
            else:
                entry['type'] = 'item'
                entry['obj'] = self.itemModel.load(entry['itemId'], force=True,
                                                   fields=self.objFields)

    def checkOwnership(self, user, session):
        if 'ownerId' in session:
            ownerId = session['ownerId']
        else:
            ownerId = session['userId']
        if ownerId != user['_id']:
            raise AccessException('Current user is not the session owner')

    def deleteSession(self, user, session):
        self.checkOwnership(user, session)
        self.remove(session)
        events.trigger('dm.sessionDeleted', info=session)

    def addFilesToSession(self, user, session, dataSet):
        """
        Add some files to a session.

        :param user: The user requesting the operation
        :param session: The session to which to add the files
        :param dataSet: A data set containing the files to be added
        """
        self.checkOwnership(user, session)

        session['dataSet'].addFiles(dataSet)
        self.save(session)

        return session

    def removeFilesFromSession(self, user, session, dataSet):
        """
        Remove files from a session.

        :param user: The user requesting the operation
        :param session: The session from which the files are to be removed
        :param dataSet: A data set containing the files to be removed
        """
        self.checkOwnership(user, session)

        session['dataSet'].removeFiles(dataSet)
        self.save(session)

        return session

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
            rootPath = obj['mountPoint']
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
