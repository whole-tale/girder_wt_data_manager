#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import boundHandler
from girder.constants import AccessType, TokenScope
from girder.models.folder import Folder as FolderModel


@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Convert folder to dataSet')
    .responseClass('DataSet')
    .modelParam('id', 'The ID of the folder.', model=FolderModel, level=AccessType.READ)
    .errorResponse('ID was invalid.')
    .errorResponse('Read access was denied for the folder.', 403)
)
@boundHandler()
def folderToDataset(self, folder):
    def _recurse(folder, current_path, user):
        data_set = []
        for item in FolderModel().childItems(folder=folder):
            data_set.append({
                'itemId': str(item['_id']),
                'mountPoint': os.path.join(current_path, item['name'])
            })
        for child_folder in FolderModel().childFolders(
                parentType='folder', parent=folder, user=user):
            data_set.append({
                'itemId': str(child_folder['_id']),
                'mountPoint': os.path.join(current_path, child_folder['name'])
            })
            data_set += _recurse(
                child_folder,
                os.path.join(current_path, child_folder['name']),
                user
            )
        return data_set

    return _recurse(folder, '/', self.getCurrentUser())
