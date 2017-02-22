#!/usr/bin/env python
# -*- coding: utf-8 -*-

import constants
from resources import session, dm
from girder.utility import setting_utilities
from girder.constants import SettingDefault


@setting_utilities.validator({
    constants.PluginSettings.PRIVATE_STORAGE_PATH
})
def validateOtherSettings(event):
    pass


def load(info):

    session = resources.session.Session()

    info['apiRoot'].dm = resources.dm.DM()
    info['apiRoot'].dm.route('GET', ('session',), session.listSessions)
    info['apiRoot'].dm.route('GET', ('session', ':id',), session.getSession)
    info['apiRoot'].dm.route('POST', ('session',), session.createSession)
    info['apiRoot'].dm.route('DELETE', ('session', ':id'), session.removeSession)

    SettingDefault.defaults[constants.PluginSettings.PRIVATE_STORAGE_PATH] = '/home/mike/work/wt/ps'
