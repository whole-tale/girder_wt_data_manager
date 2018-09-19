#!/usr/bin/env python
# -*- coding: utf-8 -*-
from girder.api.docs import addModel


dataSetItemSchema = {
    'title': 'dataSetItem',
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'description': 'A schema representing data elements used in DMS dataSets',
    'type': 'object',
    'properties': {
        'itemId': {
            'type': 'string',
            'description': 'ID of a Girder item or a Girder folder'
        },
        'mountPath': {
            'type': 'string',
            'description': 'An absolute path where the item/folder are mounted in the EFS'
        }
    },
    'required': ['itemId', 'mountPath']
}

dataSetSchema = {
    'title': 'A list of resources with a corresponding mount points in the ESF',
    '$schema': 'http://json-schema.org/draft-04/schema#',
    'type': 'array',
    'items': dataSetItemSchema,
}

addModel('dataSet', dataSetSchema)
