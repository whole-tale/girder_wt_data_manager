class DMDataSet:
    def __init__(self, doc = {}):
        self.doc = doc

    def addFiles(self, other):
        for itemId in other.doc:
            item = other.doc[itemId]
            if itemId in self.doc:
                existing = self.doc[itemId]
                existing['mountPath'] = item['mountPath']
                existing['externalUrl'] = item['externalUrl']
            else:
                self.doc.append(item)

    def removeFiles(self, other):
        for itemId in other.doc:
            if itemId in self.doc:
                del self.doc[itemId]