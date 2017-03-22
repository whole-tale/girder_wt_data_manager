from girder.constants import SettingDefault
from .. import constants

class PathMapper:
    def getPSPath(self, itemId):
        root = SettingDefault.defaults[constants.PluginSettings.PRIVATE_STORAGE_PATH]
        sItemId = str(itemId)
        return root + '/' + sItemId[0] + '/' + sItemId[1] + '/' + sItemId