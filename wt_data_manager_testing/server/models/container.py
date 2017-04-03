#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bson import json_util

from bson import objectid
from girder import events
from girder.constants import AccessType
from girder.models.model_base import AccessControlledModel, AccessException
from girder.plugins.wt_data_manager.models.session import Session
from girder import logger
from ..lib import efs
from girder.api import rest
from girder.models.setting import Setting
from girder.plugins.wt_data_manager.constants import PluginSettings


class Container(AccessControlledModel):
    def initialize(self):
        self.name = 'container'
        self.exposeFields(level = AccessType.READ, fields = {'_id', 'status', 'sessionId', 'error', 'ownerId'})

    def validate(self, container):
        return container

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
        cursor = self.find({'ownerId': userId}, sort = sort)

        for r in self.filterResultsByPermission(cursor = cursor, user = user,
            level = AccessType.READ, limit = limit, offset = offset):
            yield r

    def createContainer(self, user, dataSet):
        """
        Create a new container.

        :param user: The user creating the container.
        :type user: dict or None
        """

        dmSession = Session()
        session = dmSession.createSession(user, dataSet)

        container = {
            '_id': objectid.ObjectId(),
            'ownerId': user['_id'],
            'status': 'Starting',
            'sessionId': session['_id']
        }

        self.setUserAccess(container, user = user, level = AccessType.ADMIN)

        container = self.save(container)

        self.startContainer(user, container)
        logger.info("Container " + str(container['_id']) + " started")

        return container

    def startContainer(self, user, container):
        """
        Starts a container.

        :param user: The current user.
        :param container: The container to start.
        """

        if container['ownerId'] != user['_id']:
            raise AccessException("This container is not yours")
        container['status'] = "Starting"
        self.save(container)
        event = events.trigger('container.start', info = container)

        self._startContainer(container)
        return container

    def stopContainer(self, user, container):
        """
        Stops a container.

        :param user: The current user.
        :param container: The container to stop.
        """

        if container['ownerId'] != user['_id']:
            raise AccessException("This container is not yours")
        container['status'] = 'Stopping'
        self.save(container)
        event = events.trigger('container.stop', info = container)
        self._stopContainer(container)

        return container

    def removeContainer(self, user, container):
        if container['ownerId'] != user['_id']:
            raise AccessException("This container is not yours")

        try:
            self._stopContainer(container)
        except:
            # some of these things need to be properly synchronized
            logger.info("Could not stop container")

        self.remove(container)


    def _startContainer(self, container):
        settings = Setting()
        psRoot = settings.get(PluginSettings.PRIVATE_STORAGE_PATH)
        restUrl = rest.getApiUrl()
        token = rest.getCurrentToken()['_id']
        sessionId = str(container['sessionId'])
        mountId = efs.mount(sessionId, '/tmp/' + sessionId, psRoot, restUrl, token)
        container['mountId'] = mountId
        container['status'] = 'Running'
        self.save(container)

    def _stop_container(self, container):
        mountId = container['mountId']
        if mountId:
            efs.unmount(mountId)
            container['mountId'] = None
        container['status'] = 'Stopped'
        self.save(container)
