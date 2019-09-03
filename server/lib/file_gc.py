from __future__ import with_statement

from .tm_utils import Models
from ..models.lock import Lock
from ..models.psinfo import PSInfo
from .. import constants
import os
import time
import datetime
import threading
from threading import Thread
from girder import logger


BEGINNING_OF_TIME = datetime.datetime.fromtimestamp(0)


class FileGC:
    def __init__(self, settings, pathMapper):
        self.settings = settings
        self.lockModel = Models.lockModel
        self.pathMapper = pathMapper

    def deleteFile(self, itemId):
        if self.lockModel.tryLockForDeletion(itemId):
            try:
                path = self.pathMapper.getPSPath(itemId)
                os.remove(path)
                self.lockModel.fileDeleted(itemId)
                return True
            except FileNotFoundError:
                # well, well, wasn't there to begin with
                logger.warn('File for %s did not exist' % itemId)
                self.lockModel.fileDeleted(itemId)
                return True
            finally:
                self.lockModel.unlockForDeletion(itemId)
        else:
            return False

    def clearCache(self, force):
        if force:
            items = self.lockModel._getAllCachedItems()
        else:
            items = self.lockModel.getCollectionCandidates()
        for item in items:
            if force:
                for lock in self.lockModel._getLocksForItem(item):
                    self.lockModel.releaseLock(None, lock)
                self.lockModel._resetLockedCount(item)
            self.collectFile(item)

    def unreacheable(self, itemId):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def getCollectionCandidates(self):
        return list(self.lockModel.getCollectionCandidates())

    def collectFile(self, item):
        return self.deleteFile(item['_id'])


class DummyFileGC(FileGC):
    def __init__(self, settings, pathMapper):
        FileGC.__init__(self, settings, pathMapper)


class CollectorThread(Thread):
    def __init__(self, settings, collector):
        Thread.__init__(self, name='DM File GC')
        self.daemon = True
        self.settings = settings
        self.collector = collector

    def run(self):
        while True:
            try:
                logger.info('Running DM file GC')
                self.collect()
            except Exception:
                logger.error('File collection failure', exc_info=1)
            time.sleep(self.settings.get(constants.PluginSettings.GC_RUN_INTERVAL))

    def collect(self):
        self.collector.collect()


class PeriodicFileGC(FileGC):
    def __init__(self, settings, pathMapper, collectionStrategy):
        FileGC.__init__(self, settings, pathMapper)
        self.paused = False
        self.collectLock = threading.Lock()
        self.collectionStrategy = collectionStrategy
        self.psInfo = PSInfo()
        self.thread = CollectorThread(settings, self)
        self.thread.start()

    def collect(self):
        with self.collectLock:
            if self.paused:
                return
            self._collect()

    def _collect(self):
        # If total used space is over some collectThreshold, possibly a percentage of total space:
        #   - List all items that are cached and not locked.
        #   - Then sort them according to the collectionStrategy
        #   - Delete them one by one until we are under cleanThreshold

        if self.shouldCollect():
            candidates = self.getCollectionCandidates()
            used = 0
            for c in candidates:
                used = used + self.fileSize(c)

            self.sortCandidates(candidates)

            collected = 0
            for c in candidates:
                if self.collectFile(c):
                    collected = collected + self.fileSize(c)
                    if self.shouldStopCollecting(used, collected):
                        # keep an authoritative account of space used that isn't likely to drift
                        self.updateUsedSpace(used - collected)
                        break
                else:
                    logger.info('Did not delete file %s' % c['_id'])

    def shouldCollect(self):
        return self.collectionStrategy.shouldCollect(
            self.psInfo.totalSize(), self.psInfo.sizeUsed())

    def fileSize(self, item):
        return item['size']

    def sortCandidates(self, list):
        list.sort(key=lambda x: self.collectionStrategy.itemSortKey(x))

    def shouldStopCollecting(self, initialUsed, collected):
        return self.collectionStrategy.shouldStopCollecting(
            self.psInfo.totalSize(), initialUsed, collected)

    def updateUsedSpace(self, used):
        self.psInfo.updateInfo(used)

    def pause(self):
        with self.collectLock:
            self.paused = True

    def resume(self):
        self.paused = False


class CollectionStrategy:
    def __init__(self, collectionThresholds, sortingScheme):
        self.collectionThresholds = collectionThresholds
        self.sortingScheme = sortingScheme

    def shouldCollect(self, totalSize, usedSize):
        return self.collectionThresholds.shouldCollect(totalSize, usedSize)

    def shouldStopCollecting(self, totalSize, initialUsed, collected):
        return self.collectionThresholds.shouldStopCollecting(totalSize, initialUsed, collected)

    def itemSortKey(self, item):
        return self.sortingScheme.itemSortKey(item)


class CollectionThresholds:
    def __init__(self, settings):
        self.settings = settings

    def shouldCollect(self, totalSize, usedSize):
        raise NotImplementedError()

    def shouldStopCollecting(self, totalSize, initialUsed, collected):
        raise NotImplementedError()


class FractionalCollectionThresholds(CollectionThresholds):
    def __init__(self, settings):
        CollectionThresholds.__init__(self, settings)

    def shouldCollect(self, totalSize, usedSize):
        return usedSize > totalSize * self.getCollectStartFraction()

    def shouldStopCollecting(self, totalSize, initialUsed, collected):
        return (initialUsed - collected) <= totalSize * self.getCollectEndFraction()

    def getCollectStartFraction(self):
        return self.settings.get(constants.PluginSettings.GC_COLLECT_START_FRACTION)

    def getCollectEndFraction(self):
        return self.settings.get(constants.PluginSettings.GC_COLLECT_END_FRACTION)


class CollectionSortingScheme:
    def __init__(self):
        pass

    def itemSortKey(self, item):
        raise NotImplementedError()


class LRUSortingScheme(CollectionSortingScheme):
    def __init__(self):
        CollectionSortingScheme.__init__(self)

    def itemSortKey(self, item):
        if Lock.FIELD_LAST_UNLOCKED in item:
            return item[Lock.FIELD_LAST_UNLOCKED]
        else:
            logger.warning('Item %s does not have a dm.lastUnlocked field.' % item['_id'])
            return BEGINNING_OF_TIME
