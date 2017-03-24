#!/usr/bin/env python
# -*- coding: utf-8 -*-

class PluginSettings:
    PRIVATE_STORAGE_PATH = 'dm.private_storage_path'
    PRIVATE_STORAGE_CAPACITY = 'dm.private_storage_capacity'
    GC_RUN_INTERVAL = 'dm.gc_run_interval'
    GC_COLLECT_START_FRACTION = 'dm.gc_collect_start_fraction'
    GC_COLLECT_END_FRACTION = 'dm.gc_collect_end_fraction'

class TransferStatus:
    INITIALIZING = 0
    QUEUED = 1
    TRANSFERRING = 2
    DONE = 3
    FAILED = 4
