from .tm_utils import Models


class CacheManager:
    def __init__(self, settings, transferManager, fileGC, pathMapper):
        self.settings = settings
        self.transferManager = transferManager
        self.fileGC = fileGC
        self.pathMapper = pathMapper
        self.lockModel = Models.lockModel

    def itemLocked(self, user, itemId, sessionId):
        pass

    def itemUnlocked(self, itemId):
        pass

    def fileDownloaded(self, info):
        pass

    def sessionCreated(self, info):
        pass

    def sessionDeleted(self, info):
        pass

    def clearCache(self, force):
        self.fileGC.clearCache(force)


class SimpleCacheManager(CacheManager):
    def __init__(self, settings, transferManager, fileGC, pathMapper):
        CacheManager.__init__(self, settings, transferManager, fileGC, pathMapper)

    def itemLocked(self, user, itemId, sessionId):
        # initiates transfer immediately
        self.transferManager.startTransfer(user, itemId, sessionId)
        CacheManager.itemLocked(self, user, itemId, sessionId)

    def itemUnlocked(self, itemId):
        # notifies GC
        self.fileGC.unreacheable(itemId)
        CacheManager.itemUnlocked(self, itemId)

    def fileDownloaded(self, info):
        self.lockModel.fileDownloaded(info)

    def sessionCreated(self, session):
        # do nothing; we transfer on open()
        pass

    def sessionDeleted(self, session):
        # also nothing; we mark as unused on close()
        pass
