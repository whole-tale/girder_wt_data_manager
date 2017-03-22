#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson import json_util

from girder import events
import json
from girder.api.rest import Resource
from girder.api.rest import filtermodel, loadmodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, describeRoute

class Container(Resource):
    def initialize(self):
        self.name = 'container'

        self.exposeFields(level = AccessType.READ, fields = {'_id', 'status', 'error', 'ownerId', 'sessionId'})

    def validate(self, container):
        return container

    @access.user
    @filtermodel(model='container', plugin='wt_data_manager_testing')
    @describeRoute(
        Description('List containers for a given user.')
    )
    def listContainers(self, params):
        user = self.getCurrentUser()
        return list(self.model('container', 'wt_data_manager_testing').list(user=user))

    @access.user
    @filtermodel(model='container', plugin='wt_data_manager_testing')
    @describeRoute(
        Description('List containers for a given user.')
    )
    def listContainersFake(self, params):
        return [{'_id': 1000, 'error': None}, {'_id': 1001, 'error': "Failed to start"}]

    @access.user
    @loadmodel(model='container', plugin='wt_data_manager_testing', level=AccessType.READ)
    @describeRoute(
        Description('Get a container by ID.')
            .param('id', 'The ID of the container.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Read access was denied for the container.', 403)
    )
    @filtermodel(model='container', plugin='wt_data_manager_testing')
    def getContainer(self, container, params):
        return container

    @access.user
    @loadmodel(model='container', plugin='wt_data_manager_testing', level=AccessType.WRITE)
    @describeRoute(
        Description('Stop an existing container.')
            .param('id', 'The ID of the container.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Access was denied for the container.', 403)
    )
    def stopContainer(self, container, params):
        user = self.getCurrentUser()
        return self.model('container', 'wt_data_manager_testing').stopContainer(user, container)

    @access.user
    @loadmodel(model='container', plugin='wt_data_manager_testing', level=AccessType.WRITE)
    @describeRoute(
        Description('Starts a stopped container.')
            .param('id', 'The ID of the container.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Access was denied for the container.', 403)
    )
    def startContainer(self, container, params):
        user = self.getCurrentUser()
        return self.model('container', 'wt_data_manager_testing').startContainer(user, container)

    @access.user
    @loadmodel(model='container', plugin='wt_data_manager_testing', level=AccessType.WRITE)
    @describeRoute(
        Description('Removes (and possibly stops) a container.')
            .param('id', 'The ID of the container.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Access was denied for the container.', 403)
    )
    def removeContainer(self, container, params):
        user = self.getCurrentUser()
        return self.model('container', 'wt_data_manager_testing').removeContainer(user, container)

    @access.user
    @describeRoute(
        Description('Starts a container.').
            param('dataSet', 'An optional data set to initialize the container with. '
                             'A data set is a list of objects of the form '
                             '{"itemId": string, "mountPath": string, "externalUrl": string}.')
    )
    def createContainer(self, params):
        user = self.getCurrentUser()
        sDataSet = params.get('dataSet', '{}')
        print("Data set param: " + str(sDataSet))
        dataSet = json.loads(sDataSet)
        return self.model('container', 'wt_data_manager_testing').createContainer(user, dataSet['value'])

    def stripQuotes(self, str):
        if (str[0] == '\'' and str[-1] == '\'') or (str[0] == '"' and str[-1] == '"'):
            return str[1:-1]
