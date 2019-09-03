from .handlers.local import Local
from .handlers.http import Http
from .handlers.globus import Globus


class HandlerFactory:
    def __init__(self):
        self.loadHandlers()

    def loadHandlers(self):
        # I'm not sure if dynamic loading is worth the cost in testability, etc.
        self.handlers = {}
        self.handlers['local'] = Local
        self.handlers['http'] = Http
        self.handlers['https'] = Http
        self.handlers['file'] = Local
        self.handlers['globus'] = Globus

    def getURLTransferHandler(self, url, transferId, itemId, psPath, user, transferManager):
        if url is None or url == '':
            raise ValueError()
        ix = url.find('://')
        if ix == -1:
            return self.newTransferHandler('local', url, transferId, itemId, psPath, user,
                                           transferManager)
        else:
            proto = url[0:ix]
            return self.newTransferHandler(proto, url, transferId, itemId, psPath, user,
                                           transferManager)

    def newTransferHandler(self, name, url, transferId, itemId, psPath, user, transferManager):
        if name not in self.handlers:
            raise ValueError('No such handler: "' + name + '"')
        return self.handlers[name](url, transferId, itemId, psPath, user, transferManager)
