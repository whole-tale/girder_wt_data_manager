#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson import json_util

from girder import events
from girder.api.rest import Resource
from girder.api.rest import filtermodel, loadmodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, describeRoute

class Transfer(Resource):
    def initialize(self):
        self.name = 'transfer'
        self.exposeFields(level = AccessType.READ, fields = {'_id', 'ownerId', 'sessionId',
            'itemId', 'status', 'error', 'size', 'transferred', 'path', 'startTime', 'endTime'})

    def validate(self, transfer):
        return transfer

    @access.user
    @filtermodel(model='transfer', plugin='wt_data_manager')
    @describeRoute(
        Description('List transfers for a given user.')
    )
    def listTransfers(self, params):
        user = self.getCurrentUser()
        return list(self.model('transfer', 'wt_data_manager').list(user = user))

    @access.user
    @loadmodel(model='session', plugin='wt_data_manager')
    @filtermodel(model='transfer', plugin='wt_data_manager')
    @describeRoute(
        Description('List transfers for a given user and session.')
    )
    def listTransfersForSession(self, session, params):
        user = self.getCurrentUser()
        return list(self.model('transfer', 'wt_data_manager').list(user = user, sessionId = session['_id']))
