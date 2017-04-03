from .. import constants


class PathMapper:
    def __init__(self, settings):
        self.settings = settings

    def getPSPath(self, itemId):
        root = self.settings.get(constants.PluginSettings.PRIVATE_STORAGE_PATH)
        sItemId = str(itemId)
        return root + '/' + sItemId[0] + '/' + sItemId[1] + '/' + sItemId
