#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson import json_util

from girder import events
from girder.api.rest import Resource
from girder.api.rest import filtermodel, loadmodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.plugins.wt_data_manager.models.session import Session

class Testing(Resource):
    def initialize(self):
        self.name = 'testing'

    @access.user
    @describeRoute(
        Description('Create test items.')
    )
    def createTestItems(self, params):
        user = self.getCurrentUser()
        events.daemon.trigger('dm.testing.createItems', info={"user": user})
        return "OK"

    @access.user
    @describeRoute(
        Description('Delete all user sessions.')
    )
    def deleteSessions(self, params):
        user = self.getCurrentUser()
        model = Session()

        cursor = model.find({'userId': user['_id']})

        for r in model.filterResultsByPermission(cursor=cursor, user=user, level=AccessType.READ):
            model.remove(r)
