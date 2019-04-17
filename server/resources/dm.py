#!/usr/bin/env python
# -*- coding: utf-8 -*-

from girder.api.rest import Resource
from girder.utility.model_importer import ModelImporter
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute


class DM(Resource):
    def __init__(self, cacheManager):
        super(DM, self).__init__()
        self.resourceName = 'dm'
        self.sessionModel = ModelImporter.model('session', 'wt_data_manager')
        self.cacheManager = cacheManager

    def createSession(self, user, dataSet):
        return self.sessionModel.createSession(user, dataSet)

    def deleteSession(self, user, sessionId=None, session=None):
        if session is None:
            if sessionId is None:
                raise ValueError('One of sessionId or session must be non-null')
            session = self.sessionModel.load(sessionId, user=user)
        self.sessionModel.deleteSession(user, session)

    def getFileGC(self):
        return self.cacheManager.fileGC

    @access.admin
    @autoDescribeRoute(
        Description('Clean the DMS cache. Will not affect items being currently downloaded.')
        .param('force', 'By default, only items that are not locked are evicted from the '
               'cache. That is, items that would otherwise be collectable by the '
               'garbage collector. If this parameter is set, evict all items from the '
               'cache and forcibly remove all locks associated with them. This is not '
               'recommended since the consequences to the consistency of the system '
               'are hard to predict.', default=False, required=False, dataType='boolean')
        .errorResponse('Admin access required.', 403)
    )
    def clearCache(self, force):
        self.cacheManager.clearCache(force)
