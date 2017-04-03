from .. import constants
from girder.models.model_base import Model
from girder.constants import AccessType


# Holds information about the private storage
class PSInfo(Model):
    def initialize(self):
        self.name = 'psinfo'
        self.exposeFields(level=AccessType.READ, fields={'_id', 'used'})

    def validate(self, psinfo):
        return psinfo

    def updateInfo(self, used=0):
        self.update({}, {'$set': {'used': used}})

    def getInfo(self):
        dict = self.findOne()
        if dict is None:
            dict = {'used': 0}
        dict['capacity'] = \
            self.model('setting').get(constants.PluginSettings.PRIVATE_STORAGE_CAPACITY)
        return dict

    def totalSize(self):
        return self.model('setting').get(constants.PluginSettings.PRIVATE_STORAGE_CAPACITY)

    def sizeUsed(self):
        return self.getInfo()['capacity']
