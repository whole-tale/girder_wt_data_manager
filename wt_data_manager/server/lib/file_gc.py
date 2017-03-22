from ..models.lock import Lock
import os

class FileGC():
    def __init__(self, pathMapper):
        self.lockModel = Lock()
        self.pathMapper = pathMapper

    def deleteFile(self, itemId):
        if self.lockModel.tryLockForDeletion(itemId):
            try:
                path = self.pathMapper.getPSPath(itemId)
                os.remove(path)
                self.lockModel.fileDeleted(itemId)
            finally:
                self.lockModel.unlockForDeletion(itemId)

    def unreacheable(self, itemId):
        pass

class DummyFileGC(FileGC):
    def __init__(self, pathMapper):
        FileGC.__init__(self, pathMapper)
