#!/usr/bin/env python
# -*- coding: utf-8 -*-


from girder.api.rest import Resource, RestException
from girder.api.rest import filtermodel, loadmodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, describeRoute
import json

class Session(Resource):
    def initialize(self):
        self.name = 'session'
        self.exposeFields(level = AccessType.READ, fields = {'_id', 'dataSet', 'ownerId'})

    def validate(self, session):
        return session

    @access.user
    @filtermodel(model='session', plugin='wt_data_manager')
    @describeRoute(
        Description('List sessions for a given user.')
    )
    def listSessions(self, params):
        user = self.getCurrentUser()
        return list(self.model('session', 'wt_data_manager').list(user=user))

    @access.user
    @loadmodel(model='session', plugin='wt_data_manager', level=AccessType.READ)
    @describeRoute(
        Description('Get a session by ID.')
            .param('id', 'The ID of the session.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Read access was denied for the session.', 403)
    )
    @filtermodel(model='session', plugin='wt_data_manager')
    def getSession(self, session, params):
        return session

    @access.user
    @loadmodel(model='session', plugin='wt_data_manager', level=AccessType.WRITE)
    @describeRoute(
        Description('Removes an existing session.')
            .param('id', 'The ID of the session.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Access was denied for the session.', 403)
    )
    def removeSession(self, session, params):
        user = self.getCurrentUser()
        return self.model('session', 'wt_data_manager').deleteSession(user, session)

    @access.user
    @describeRoute(
        Description('Creates a session.').
            param('dataSet', 'An optional data set to initialize the session with. '
                             'A data set is a list of objects of the form '
                             '{"itemId": string, "mountPath": string}.', paramType='query')
    )
    def createSession(self, params):
        user = self.getCurrentUser()
        dataSet = json.loads(params.get('dataSet', '[]'))
        return self.model('session', 'wt_data_manager').createSession(user, dataSet)

    @access.user
    @loadmodel(model='session', plugin='wt_data_manager', level=AccessType.READ)
    @describeRoute(
        Description('Get an object in a session using a path.')
            .param('id', 'The ID of the session.', paramType='path')
            .param('path', 'The path of the object, starting from the mount point.', paramType='query')
            .param('children', 'Whether to also return a listing of all the children '
                'of the object at the specified path', paramType='query')
            .errorResponse('ID was invalid.')
            .errorResponse('Read access was denied for the session.', 403)
            .errorResponse('Object was not found.', 401)
    )
    def getObject(self, session, params):
        user = self.getCurrentUser()
        children = False
        if 'children' in params:
            children = True
        try:
            return self.model('session', 'wt_data_manager').getObject(user, session, params['path'], children)
        except LookupError as ex:
            raise RestException(ex.message, code = 401)
