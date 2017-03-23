#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .resources import container, testing
from .models import container as cm

def load(info):

    container = resources.container.Container()

    # assume that wt_data_manager is loaded first and .dm exists
    info['apiRoot'].dm.route('GET', ('testing', 'container'), container.listContainers)
    info['apiRoot'].dm.route('GET', ('testing', 'container', ':id',), container.getContainer)
    info['apiRoot'].dm.route('POST', ('testing', 'container'), container.createContainer)
    info['apiRoot'].dm.route('GET', ('testing', 'container', ':id', 'start'), container.startContainer)
    info['apiRoot'].dm.route('GET', ('testing', 'container', ':id', 'stop'), container.stopContainer)
    info['apiRoot'].dm.route('DELETE', ('testing', 'container', ':id',), container.removeContainer)

    testing = resources.testing.Testing()

    info['apiRoot'].dm.route('POST', ('testing', 'createItems'), testing.createTestItems)
    info['apiRoot'].dm.route('GET', ('testing', 'createItems'), testing.createTestItems)

    info['apiRoot'].dm.route('GET', ('testing', 'deleteSessions',), testing.deleteSessions)
