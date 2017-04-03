
class CacheManager:
    def __init__(self, settings, transferManager, fileGC, pathMapper, lockModel):
        self.settings = settings
        self.transferManager = transferManager
        self.fileGC = fileGC
        self.pathMapper = pathMapper
        self.lockModel = lockModel

    def itemLocked(self, user, itemId, sessionId):
        pass

    def itemUnlocked(self, itemId):
        pass

    def fileDownloaded(self):
        pass

    def sessionCreated(self):
        pass

    def sessionDeleted(self):
        pass


class SimpleCacheManager(CacheManager):
    def __init__(self, settings, transferManager, fileGC, pathMapper, lockModel):
        CacheManager.__init__(self, settings, transferManager, fileGC, pathMapper, lockModel)

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
