#!/usr/bin/env python
# -*- coding: utf-8 -*-


from girder.api.rest import Resource
from girder.api.rest import filtermodel, loadmodel
from girder.constants import AccessType
from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.exceptions import RestException
from ..models.session import Session


class Lock(Resource):
    def initialize(self):
        self.name = 'lock'
        self.exposeFields(level=AccessType.READ,
                          fields={'_id', 'userId', 'sessionId', 'itemId', 'ownerId'})

    def validate(self, session):
        return session

    @access.user
    @filtermodel(model='lock', plugin='wt_data_manager')
    @describeRoute(
        Description('List locks for a given user.')
        .param('sessionId', 'Restrict results to a single session',
               paramType='query', required=False)
        .param('itemId', 'Only return locks on a given item',
               paramType='query', required=False)
        .param('ownerId', 'Only return locks with a specific lock owner',
               paramType='query', required=False)
    )
    def listLocks(self, params):
        user = self.getCurrentUser()
        sessionId = None
        itemId = None
        ownerId = None
        if 'sessionId' in params:
            sessionId = params['sessionId']
        if 'itemId' in params:
            itemId = params['itemId']
        if 'ownerId' in params:
            ownerId = params['ownerId']
        return list(self.model('lock', 'wt_data_manager').listLocks(user=user, sessionId=sessionId,
                                                                    itemId=itemId, ownerId=ownerId))

    @access.user
    @loadmodel(model='session', plugin='wt_data_manager', level=AccessType.READ)
    @filtermodel(model='lock', plugin='wt_data_manager')
    @describeRoute(
        Description('List locks for a given user.')
        .param('sessionId', 'Restrict results to a single session', paramType='path')
    )
    def listLocksForSession(self, session, params):
        user = self.getCurrentUser()
        return list(self.model('lock', 'wt_data_manager').listLocks(user=user,
                                                                    sessionId=session['_id']))

    @access.user
    @loadmodel(model='lock', plugin='wt_data_manager', level=AccessType.READ)
    @describeRoute(
        Description('Get a lock by ID.')
        .param('id', 'The ID of the lock.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the lock.', 403)
    )
    @filtermodel(model='lock', plugin='wt_data_manager')
    def getLock(self, lock, params):
        return lock

    @access.user
    @loadmodel(model='lock', plugin='wt_data_manager', level=AccessType.WRITE)
    @describeRoute(
        Description('Removes an existing lock.')
        .param('id', 'The ID of the lock.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the lock.', 403)
    )
    def releaseLock(self, lock, params):
        user = self.getCurrentUser()
        return self.model('lock', 'wt_data_manager').releaseLock(user, lock)

    @access.user
    @describeRoute(
        Description('Acquires a lock on an item.')
        .param('sessionId', 'A Data Manager session.', paramType='query')
        .param('itemId', 'The item to lock', paramType='query')
        .param('ownerId', 'The lock owner.', paramType='query', required=False)
        .errorResponse('Item not in session.', 404)
    )
    def acquireLock(self, params):
        user = self.getCurrentUser()
        sessionId = params['sessionId']
        itemId = params['itemId']
        ownerId = None
        if 'ownerId' in params:
            ownerId = params['ownerId']
        if not Session().containsItem(sessionId, itemId, user):
            raise RestException('Item not in the session', 404)
        return self.model('lock', 'wt_data_manager').acquireLock(user, sessionId, itemId, ownerId)

    @access.user
    @loadmodel(model='lock', plugin='wt_data_manager', level=AccessType.READ)
    @describeRoute(
        Description('Download the item locked by a lock.')
        .param('id', 'The ID of the lock.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Access was denied for the lock.', 403)
    )
    def downloadItem(self, lock, params):
        return self.model('lock', 'wt_data_manager').downloadItem(lock)

    @access.user
    @describeRoute(
        Description('Evict an item from the cache.')
            .param('id', 'The ID of the item.', paramType='path')
            .errorResponse('ID was invalid.')
            .errorResponse('Access was denied for the lock.', 403)
    )
    def evict(self, id, params):
        return self.model('lock', 'wt_data_manager').evict(id)
