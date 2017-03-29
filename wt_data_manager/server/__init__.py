#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .constants import PluginSettings
from .resources.session import Session
from .resources.lock import Lock
from .resources.transfer import Transfer
from .resources.dm import DM
from .models import lock as lock_model
from girder.models.setting import Setting
from girder.utility import setting_utilities
from girder.constants import SettingDefault
from .lib import transfer_manager, file_gc, cache_manager, path_mapper
from girder import events
import traceback


@setting_utilities.validator({
    PluginSettings.PRIVATE_STORAGE_PATH,
    PluginSettings.PRIVATE_STORAGE_CAPACITY,
    PluginSettings.GC_RUN_INTERVAL
})
def validateOtherSettings(event):
    pass


def load(info):
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB
    SettingDefault.defaults[PluginSettings.PRIVATE_STORAGE_PATH] = '/home/mike/work/wt/ps'
    SettingDefault.defaults[PluginSettings.PRIVATE_STORAGE_CAPACITY] = 100 * GB
    # run collection every 10 minutes
    SettingDefault.defaults[PluginSettings.GC_RUN_INTERVAL] = 10 * 60
    # only collect if over %50 used
    SettingDefault.defaults[PluginSettings.GC_COLLECT_START_FRACTION] = 0.5
    # stop collecting when below %50 usage
    SettingDefault.defaults[PluginSettings.GC_COLLECT_END_FRACTION] = 0.5

    settings = Setting()
    session = Session()
    lock = Lock()
    transfer = Transfer()

    lockModel = lock_model.Lock()
    pathMapper = path_mapper.PathMapper(settings)
    transferManager = transfer_manager.DelayingSimpleTransferManager(settings, pathMapper)

    # a GC that does nothing
    fileGC = file_gc.DummyFileGC(settings, pathMapper)
    #fileGC = file_gc.PeriodicFileGC(settings, pathMapper,
    #            file_gc.CollectionStrategy(
    #                file_gc.FractionalCollectionThresholds(settings),
    #                file_gc.LRUSortingScheme()))
    cacheManager = cache_manager.SimpleCacheManager(settings, transferManager, fileGC, pathMapper, lockModel)

    info['apiRoot'].dm = DM(session, cacheManager)
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
