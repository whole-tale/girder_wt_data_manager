#!/usr/bin/env python
# -*- coding: utf-8 -*-


from girder.api.rest import Resource, RestException
from girder.api.rest import filtermodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from ..models.session import Session as SessionModel
from ..schema.dataset import dataSetSchema


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
        return list(SessionModel().list(user=user))

    @access.user
    @filtermodel(model=SessionModel)
    @autoDescribeRoute(
        Description('Get a session by ID.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.READ)
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
        Description('Remove an existing session.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.WRITE)
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the session.', 403)
    )
    def removeSession(self, session):
        user = self.getCurrentUser()
        return SessionModel().deleteSession(user, session)

    @access.user
    @autoDescribeRoute(
        Description('Create a session.')
        .jsonParam(
            'dataSet', 'An optional data set to initialize the session with. '
            'A data set is a list of objects of the form '
            '{"itemId": string, "mountPath": string}.', paramType='query', schema=dataSetSchema,
            required=False)
        .modelParam('taleId', "An optional id of a Tale. If provided, Tale's involatileData will "
                    "be used to initialize the session instead of the dataSet parameter.",
                    model='tale', plugin='wholetale', level=AccessType.READ, paramType='query',
                    required=False)
    )
    def createSession(self, dataSet, tale):
        user = self.getCurrentUser()
        return SessionModel().createSession(user, dataSet=dataSet, tale=tale)

    @access.user
    @autoDescribeRoute(
        Description('Modify a session.')
        .notes('Specifically, allows changing the dataSet of a session, '
               'which implies the ability to add/remove folders/files from a live session. '
               'Note that removal can fail if a file is in use.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.ADMIN)
        .jsonParam('dataSet', 'An optional data set to initialize the session with. '
                              'A data set is a list of objects of the form '
                              '{"itemId": string, "mountPath": string}.', paramType='query',
                   schema=dataSetSchema)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the session.', 403)
    )
    @filtermodel(model='session', plugin='wt_data_manager')
    def modifySession(self, session, dataSet):
        user = self.getCurrentUser()
        return self.model('session', 'wt_data_manager').modifySession(user, session, dataSet)

    @access.user
    @autoDescribeRoute(
        Description('Get an object in a session using a path.')
        .modelParam('id', 'The ID of the session.', model=SessionModel, level=AccessType.READ)
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
