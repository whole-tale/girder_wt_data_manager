from girder.models.model_base import AccessControlledModel

class GirderUtils:
    @staticmethod
    def resolveDataSetGirderIds(dataSet, user):
        for dataFile in dataSet:
            GirderUtils.resolveDataFileGirderId(dataFile, user)

    @staticmethod
    def resolveDataFileGirderId(dataFile, user):
        if dataFile['externalUrl'] == None:
            id = dataFile['itemId']
            doc = AccessControlledModel.load(id, fields=['_modelType'])
            modelType = doc['_modelType']
            if modelType == 'collection' or modelType == 'folder':
                dataFile['type'] = modelType
            else:
                # it's a file
                pass
