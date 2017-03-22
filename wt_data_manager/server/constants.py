#!/usr/bin/env python
# -*- coding: utf-8 -*-

class PluginSettings:
    PRIVATE_STORAGE_PATH = 'dm.private_storage_path'

class TransferStatus:
    INITIALIZING = 0
    QUEUED = 1
    TRANSFERRING = 2
    DONE = 3
    FAILED = 4
