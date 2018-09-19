#!/usr/bin/env python
# -*- coding: utf-8 -*-


from girder.api.rest import Resource, RestException
from girder.api.rest import filtermodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, describeRoute, autoDescribeRoute
from ..models.session import Session as SessionModel
import json


class Session(Resource):
    def initialize(self):
        self.name = 'session'
        self.exposeFields(level=AccessType.READ, fields={'_id', 'dataSet', 'ownerId'})

    def validate(self, session):
        return session

    @access.user
    @filtermodel(model=SessionModel)
    @autoDescribeRoute(
        Description('List sessions for a given user.')
    )
    def listSessions(self):
        user = self.getCurrentUser()
        return list(self.model('session', 'wt_data_manager').list(user=user))

    @access.user
    @filtermodel(model=SessionModel)
    @autoDescribeRoute(
        Description('Get a session by ID.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.ADMIN)
        .param('loadObjects', 'If True, the dataSet of the returned session will contain'
                              'two additional fields for each entry: "type": "folder"|"item" '
                              'and "obj": <itemOrFolder>', dataType='boolean', required=False,
                              default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the session.', 403)
    )
    def getSession(self, session, loadObjects):
        if loadObjects:
            SessionModel().loadObjects(session['dataSet'])
        return session

    @access.user
    @autoDescribeRoute(
        Description('Removes an existing session.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.ADMIN)
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the session.', 403)
    )
    def removeSession(self, session, params):
        user = self.getCurrentUser()
        return SessionModel().deleteSession(user, session)

    @access.user
    @describeRoute(
        Description('Creates a session.')
        .param('dataSet', 'An optional data set to initialize the session with. '
               'A data set is a list of objects of the form '
               '{"itemId": string, "mountPath": string}.', paramType='query')
    )
    def createSession(self, params):
        user = self.getCurrentUser()
        dataSet = json.loads(params.get('dataSet', '[]'))
        return SessionModel().createSession(user, dataSet)

    @access.user
    @autoDescribeRoute(
        Description('Get an object in a session using a path.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.ADMIN)
        .param('path', 'The path of the object, starting from the mount point.',
               paramType='query')
        .param('children', 'Whether to also return a listing of all the children '
               'of the object at the specified path', dataType='boolean', required=False,
               default=False)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the session.', 403)
        .errorResponse('Object was not found.', 401)
    )
    def getObject(self, session, path, children):
        user = self.getCurrentUser()
        try:
            return SessionModel().getObject(user, session, path, children)
        except LookupError as ex:
            raise RestException(str(ex), code=401)
