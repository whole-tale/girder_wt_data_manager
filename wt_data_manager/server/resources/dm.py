#!/usr/bin/env python
# -*- coding: utf-8 -*-

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, loadmodel

class DM(Resource):
    def __init__(self):
        super(DM, self).__init__()
        self.resourceName = 'dm'
