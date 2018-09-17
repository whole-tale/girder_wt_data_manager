#!/usr/bin/env python
# -*- coding: utf-8 -*-


class PluginSettings:
    PRIVATE_STORAGE_PATH = 'dm.private_storage_path'
    PRIVATE_STORAGE_CAPACITY = 'dm.private_storage_capacity'
    GC_RUN_INTERVAL = 'dm.gc_run_interval'
    GC_COLLECT_START_FRACTION = 'dm.gc_collect_start_fraction'
    GC_COLLECT_END_FRACTION = 'dm.gc_collect_end_fraction'
    GLOBUS_ROOT_PATH = 'dm.globus_root_path'
    GLOBUS_CONNECT_DIR = 'dm.globus_gc_dir'
    # These are internal settings. Should not be set by the admin
    GLOBUS_ENDPOINT_ID = 'dm.globus_endpoint_id'
    GLOBUS_ENDPOINT_NAME = 'dm.globus_endpoint_name'


class GlobusEnvironmentVariables:
    GLOBUS_CLIENT_ID = 'GLOBUS_CLIENT_ID'
    GLOBUS_CLIENT_SECRET = 'GLOBUS_CLIENT_SECRET'
    GLOBUS_CONNECT_DIR = 'GLOBUS_CONNECT_DIR'
    ALL = [GLOBUS_CLIENT_ID, GLOBUS_CLIENT_SECRET, GLOBUS_CONNECT_DIR]


class TransferStatus:
    INITIALIZING = 0
    QUEUED = 1
    TRANSFERRING = 2
    DONE = 3
    FAILED = 4
