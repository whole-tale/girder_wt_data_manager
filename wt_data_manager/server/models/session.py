#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson import json_util

from bson import objectid
from girder import events
from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel, AccessException
from ..lib.data_set import DMDataSet

class Session(AccessControlledModel):
    def initialize(self):
        self.name = 'session'
        self.exposeFields(level = AccessType.READ, fields = {'_id', 'status', 'ownerId', 'error'})

    def validate(self, session):
        return session

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True,
             force=False, fields=None, exc=False):
        doc = AccessControlledModel.load(self, id, level, user, objectId, force, fields, exc)
        doc['dataSet'] = DMDataSet(doc['dataSet'])
        return doc

    def save(self, doc, validate=True, triggerEvents=True):
        dataSet = doc['dataSet']
        doc['dataSet'] = dataSet.doc
        doc = AccessControlledModel.save(self, doc, validate, triggerEvents)
        doc['dataSet'] = dataSet
        return doc

    def list(self, user, limit = 0, offset = 0, sort = None):
        """
        List a page of containers for a given user.

        :param user: The user who owns the job.
        :type user: dict or None
        :param limit: The page limit.
        :param offset: The page offset
        :param sort: The sort field.
        """
        userId = user['_id'] if user else None
        cursor = self.find({'userId': userId}, sort = sort)

        for r in self.filterResultsByPermission(cursor = cursor, user = user,
            level = AccessType.READ, limit = limit, offset = offset):
            yield r

    def createSession(self, user, dataSet = None):
        """
        Create a new session.

        :param user: The user creating the job.
        :type user: dict or None
        :param save: Whether the documented should be saved to the database.
        :type save: bool
        """

        session = {
            "_id": objectid.ObjectId(),
            "userId": user['_id'],
            "dataSet": dataSet
        }

        self.setUserAccess(session, user = user, level = AccessType.ADMIN)

        session = self.save(session)

        print "Session " + str(session['_id']) + " created"

        return session

    def deleteSession(self, user, session):
        self.remove(session)

    def addFilesToSession(self, user, session, dataSet):
        """
        Add some files to a session.

        :param user: The user requesting the operation
        :param session: The session to which to add the files
        :param dataSet: A data set containing the files to be added
        """
        if session['ownerId'] != user['_id']:
            raise AccessException('Current user is not the session owner')

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
        if session['ownerId'] != user['_id']:
            raise AccessException('Current user is not the session owner')

        session['dataSet'].removeFiles(dataSet)
        self.save(session)

        return session
