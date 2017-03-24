#!/usr/bin/env python
# -*- coding: utf-8 -*-

import constants
from resources import session, dm, lock, transfer
from models import lock as lock_model
from girder.utility import setting_utilities
from girder.constants import SettingDefault
from lib import transfer_manager, file_gc, cache_manager, path_mapper
from girder import events
import traceback


@setting_utilities.validator({
    constants.PluginSettings.PRIVATE_STORAGE_PATH
})
def validateOtherSettings(event):
    pass


def load(info):
    SettingDefault.defaults[constants.PluginSettings.PRIVATE_STORAGE_PATH] = '/home/mike/work/wt/ps'

    session = resources.session.Session()
    lock = resources.lock.Lock()
    transfer = resources.transfer.Transfer()

    lockModel = lock_model.Lock()
    pathMapper = path_mapper.PathMapper()
    transferManager = transfer_manager.DelayingSimpleTransferManager(pathMapper)
    fileGC = file_gc.DummyFileGC(pathMapper)
    cacheManager = cache_manager.SimpleCacheManager(transferManager, fileGC, pathMapper, lockModel)

    info['apiRoot'].dm = resources.dm.DM(session, cacheManager)
    info['apiRoot'].dm.route('GET', ('session',), session.listSessions)
    info['apiRoot'].dm.route('GET', ('session', ':id',), session.getSession)
    info['apiRoot'].dm.route('POST', ('session',), session.createSession)
    info['apiRoot'].dm.route('DELETE', ('session', ':id'), session.removeSession)

    info['apiRoot'].dm.route('POST', ('lock',), lock.acquireLock)
    info['apiRoot'].dm.route('DELETE', ('lock', ':id'), lock.releaseLock)
    info['apiRoot'].dm.route('GET', ('lock', ':id'), lock.getLock)
    info['apiRoot'].dm.route('GET', ('lock',), lock.listLocks)

    info['apiRoot'].dm.route('GET', ('session', ':id', 'object'), session.getObject)
    info['apiRoot'].dm.route('GET', ('session', ':id', 'lock',), lock.listLocksForSession)
    info['apiRoot'].dm.route('GET', ('session', ':id', 'transfer'), transfer.listTransfersForSession)

    info['apiRoot'].dm.route('GET', ('transfer',), transfer.listTransfers)


    def itemLocked(event):
        dict = event.info
        print("Item locked event: " + str(dict))
        try:
            cacheManager.itemLocked(dict['user'], dict['itemId'], dict['sessionId'])
        except:
            traceback.print_exc()

    def itemUnlocked(event):
        cacheManager.itemUnlocked(event.info)

    def fileDownloaded(event):
        cacheManager.fileDownloaded(event.info)

    def sessionCreated(event):
        cacheManager.sessionCreated(event.info)

    def sessionDeleted(event):
        cacheManager.sessionDeleted(event.info)

    events.bind('dm.sessionCreated', 'sessionCreated', sessionCreated)
    events.bind('dm.sessionDeleted', 'sessionDeleted', sessionDeleted)
    #TODO: add session file changes
    events.bind('dm.itemLocked', 'itemLocked', itemLocked)
    events.bind('dm.itemUnlocked', 'itemUnlocked', itemUnlocked)
    events.bind('dm.fileDownloaded', 'fileDownloaded', fileDownloaded)