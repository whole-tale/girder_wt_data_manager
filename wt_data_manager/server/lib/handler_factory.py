from .handlers.local import Local
from .handlers.http import Http


class HandlerFactory:
    def __init__(self):
        self.loadHandlers()

    def loadHandlers(self):
        # I'm not sure if dynamic loading is worth the cost in testability, etc.
        self.handlers = {}
        self.handlers['local'] = Local
        self.handlers['http'] = Http
        self.handlers['file'] = Local

    def getURLTransferHandler(self, url, transferId, itemId, psPath):
        if url is None or url == '':
            raise ValueError()
        ix = url.find('://')
        if ix == -1:
            return self.newTransferHandler('local', url, transferId, itemId, psPath)
        else:
            proto = url[0:ix]
            return self.newTransferHandler(proto, url, transferId, itemId, psPath)

    def newTransferHandler(self, name, url, transferId, itemId, psPath):
        if name not in self.handlers:
            raise ValueError('No such handler: "' + name + '"')
        return self.handlers[name](url, transferId, itemId, psPath)
