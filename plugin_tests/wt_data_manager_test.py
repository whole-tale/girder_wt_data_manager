#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tests import base
import tempfile
import time
import os
import cherrypy
import json
from bson import ObjectId
import shutil
from .httpserver import Server
# oh, boy; you'd think we've learned from #include...
# from plugins.wt_data_manager.server.constants import PluginSettings


MB = 1024 * 1024


def setUpModule():
    base.enabledPlugins.append('wt_data_manager')
    base.startServer()


def tearDownModule():
    base.stopServer()


class IntegrationTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.admin = self.model('user').createUser(
            'wt-dm-admin-user', 'password', 'Root', 'vonKlompf', 'jadmin@example.com')
        self.user = self.model('user').createUser(
            'wt-dm-test-user', 'password', 'Joe', 'User', 'juser@example.com')
        self.user2 = self.model('user').createUser(
            'wt-dm-test-user2', 'password', 'Joey', 'Black', 'jblack@example.com')
        self.tmpdir = {}
        self.assetstore = list(self.model('assetstore').find({}))[0]

        [self.testCollection, self.testFolder, self.files, self.gfiles] = \
            self.createStructure('test_')

        [self.testCollection2, self.testFolder2, self.files2, self.gfiles2] = \
            self.createStructure('test2_')

        self.apiroot = cherrypy.tree.apps['/api'].root.v1

        self.transferredFiles = set()

    def tearDown(self):
        for prefix in self.tmpdir:
            shutil.rmtree(self.tmpdir[prefix])
        base.TestCase.tearDown(self)

    def createStructure(self, prefix):
        self.tmpdir[prefix] = tempfile.mkdtemp()
        collection = \
            self.model('collection').createCollection('%s_wt_dm_test_col' % prefix,
                                                      creator=self.user, public=False,
                                                      reuseExisting=True)
        folder = \
            self.model('folder').createFolder(collection, '%s_wt_dm_test_fldr' % prefix,
                                              parentType='collection')
        files = [self.createFile('%s_%s' % (prefix, n), 1 * MB, self.tmpdir[prefix])
                 for n in range(1, 5)]
        self.model('assetstore').importData(self.assetstore, folder, 'folder',
                                            {'importPath': self.tmpdir[prefix]}, {}, self.user,
                                            leafFoldersAsItems=False)
        gfiles = [self.model('item').findOne({'name': file}) for file in files]

        return (collection, folder, files, gfiles)

    def createHttpFile(self):
        params = {
            'parentType': 'folder',
            'parentId': self.testFolder['_id'],
            'name': 'httpitem1',
            'linkUrl': self.testServer.getUrl() + '/1M',
            'size': MB
        }
        resp = self.request(path='/file', method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        self.httpItem = self.model('item').load(resp.json['itemId'], user=self.user)

    def createFile(self, suffix, size, dir):
        name = 'file' + str(suffix)
        path = dir + '/' + name
        with open(path, 'wb') as f:
            for i in range(size):
                f.write(b'\0')
        return name

    def makeDataSet(self, items, objectids=True):
        if objectids:
            return [
                {'itemId': f['_id'], 'mountPath': '/' + f['name'], '_modelType': 'item'}
                for f in items
            ]
        else:
            return [
                {'itemId': str(f['_id']), 'mountPath': '/' + f['name'], '_modelType': 'item'}
                for f in items
            ]

    def test01LocalFile(self):
        dataSet = self.makeDataSet(self.gfiles)
        self._testItem(dataSet, self.gfiles[0], True)

    def test02HttpFile(self):
        self.testServer = Server()
        self.testServer.start()
        self.createHttpFile()
        dataSet = self.makeDataSet([self.httpItem])
        self._testItem(dataSet, self.httpItem)
        self.testServer.stop()

    def test03Caching(self):
        dataSet = self.makeDataSet(self.gfiles)
        self._testItem(dataSet, self.gfiles[0])
        self._testItem(dataSet, self.gfiles[0])
        item = self.reloadItem(self.gfiles[0])
        self.assertEqual(item['dm']['downloadCount'], 1)
        self._testItem(dataSet, self.gfiles[1])

    def test04SessionApi(self):
        dataSet = self.makeDataSet(self.gfiles)
        self._testSessionApi(dataSet, self.gfiles[0])

    def test05SessionDeleteById(self):
        dataSet = self.makeDataSet(self.gfiles)
        session = self.apiroot.dm.createSession(self.user, dataSet)
        self.apiroot.dm.deleteSession(self.user, sessionId=session['_id'])

    def _testSessionApi(self, dataSet, item):
        session = self.apiroot.dm.createSession(self.user, dataSet)
        sessions = list(self.model('session', 'wt_data_manager').list(self.user))
        self.assertEqual(len(sessions), 1)
        self._testItemWithSession(session, item)
        resp = self.request(
            path='/dm/session/{_id}/object'.format(**session),
            method='GET', user=self.user,
            params={'path': '/non_existent_path'}
        )
        self.assertStatus(resp, 400)

        resp = self.request(
            path='/dm/session/{_id}/object'.format(**session),
            method='GET', user=self.user,
            params={'path': '/filetest__4'}
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['object']['_id'], str(self.gfiles[3]['_id']))

        dataSet.append({
            'itemId': str(self.testFolder2['_id']),
            'mountPath': '/' + self.testFolder2['name'],
            '_modelType': 'folder',
        })
        dataSet = [
            {'itemId': str(_['itemId']), 'mountPath': _['mountPath'], '_modelType': _['_modelType']}
            for _ in dataSet
        ]
        resp = self.request(
            path='/dm/session/{_id}'.format(**session),
            method='PUT', user=self.user,
            params={'dataSet': json.dumps(dataSet)}
        )
        self.assertStatusOk(resp)
        session = resp.json
        self.assertEqual(session['seq'], 1)

        resp = self.request(
            path='/dm/session/{_id}/object'.format(**session),
            method='GET', user=self.user,
            params={'path': '/' + self.testFolder2['name'], 'children': True}
        )
        self.assertStatusOk(resp)
        children = resp.json['children']
        leafFile = next((_ for _ in children if _['name'] == self.gfiles2[-1]['name']), None)
        self.assertEqual(leafFile['_id'], str(self.gfiles2[-1]['_id']))

        resp = self.request(
            path='/dm/session/{_id}/object'.format(**session),
            method='GET', user=self.user,
            params={'path': '/' + self.testFolder2['name'] + '/' + leafFile['name'] + '_blah',
                    'children': True}
        )
        self.assertStatus(resp, 400)

        resp = self.request(
            path='/dm/session/{_id}/object'.format(**session),
            method='GET', user=self.user,
            params={'path': '/' + self.testFolder2['name'] + '/' + leafFile['name'],
                    'children': True}
        )
        self.assertStatusOk(resp)

        resp = self.request(
            path='/dm/session/{_id}'.format(**session),
            method='DELETE', user=self.user2)
        self.assertStatus(resp, 403)

        resp = self.request(
            path='/dm/session/{_id}'.format(**session),
            method='DELETE', user=self.admin)
        self.assertStatusOk(resp)

        from girder.plugins.wholetale.models.tale import Tale
        tale = Tale().createTale({'_id': ObjectId()}, dataSet, title='blah',
                                 creator=self.user)

        resp = self.request(
            path='/dm/session', method='POST', user=self.user,
            params={'taleId': str(tale['_id'])}
        )
        self.assertStatusOk(resp)
        session = resp.json
        self.assertEqual(session['dataSet'], dataSet)
        Tale().remove(tale)  # TODO: This should fail, since the session is up
        resp = self.request(
            path='/dm/session/{_id}'.format(**session),
            method='DELETE', user=self.user)
        self.assertStatusOk(resp)

    def _testItem(self, dataSet, item, download=False):
        session = self.model('session', 'wt_data_manager').createSession(self.user, dataSet=dataSet)
        self._testItemWithSession(session, item, download=download)
        self.model('session', 'wt_data_manager').deleteSession(self.user, session)

    def _testItemWithSession(self, session, item, download=False):
        self.assertNotEqual(session, None)
        lock = self.model('lock', 'wt_data_manager').acquireLock(self.user, session['_id'],
                                                                 item['_id'])

        locks = list(self.model('lock', 'wt_data_manager').listLocks(self.user, session['_id']))
        self.assertEqual(len(locks), 1)

        self.assertNotEqual(lock, None)

        item = self.reloadItem(item)
        self.assertHasKeys(item, ['dm'])

        psPath = self.waitForFile(item)
        self.transferredFiles.add(psPath)

        transfers = self.model('transfer', 'wt_data_manager').list(self.user, discardOld=False)
        transfers = list(transfers)
        self.assertEqual(len(transfers), len(self.transferredFiles))

        if download:
            self._downloadFile(lock, item)

        self.assertTrue(os.path.isfile(psPath))
        self.assertEqual(os.path.getsize(psPath), item['size'])

        self.model('lock', 'wt_data_manager').releaseLock(self.user, lock)

        item = self.reloadItem(item)
        self.assertEqual(item['dm']['lockCount'], 0)

    def _downloadFile(self, lock, item):
        stream = self.model('lock', 'wt_data_manager').downloadItem(lock)
        sz = 0
        for chunk in stream():
            sz += len(chunk)
        self.assertEqual(sz, item['size'])

    def reloadItem(self, item):
        return self.model('item').load(item['_id'], user=self.user)

    def waitForFile(self, item, rest=False, sessionId=None):
        max_iters = 300
        while max_iters > 0:
            if 'cached' in item['dm'] and item['dm']['cached']:
                self.assertHasKeys(item['dm'], ['psPath'])
                psPath = item['dm']['psPath']
                self.assertIsNotNone(psPath)
                return psPath
            time.sleep(0.1)
            max_iters -= 1
            if rest:
                item = self.reloadItemRest(item)
            else:
                item = self.reloadItem(item)
        self.assertTrue(False, 'No file found after about 30s')

    def test06resources(self):
        dataSet = self.makeDataSet(self.gfiles, objectids=False)

        resp = self.request('/dm/session', method='POST', user=self.user, params={
            'dataSet': json.dumps(dataSet)
        })
        self.assertStatusOk(resp)
        sessionId = resp.json['_id']

        # list sessions
        resp = self.request('/dm/session', method='GET', user=self.user)
        self.assertStatusOk(resp)

        # get session
        resp = self.request('/dm/session/%s' % sessionId, method='GET', user=self.user, params={
            'loadObjects': 'true'
        })
        self.assertStatusOk(resp)
        self.assertEqual(sessionId, str(resp.json['_id']))

        item = self.gfiles[0]

        # This coverage business, as implemented, is wrong really. Both branches of
        # a condition should be tested, including a failing condition with no else block.
        resp = self.request('/dm/lock', method='POST', user=self.user, params={
            'sessionId': sessionId,
            'itemId': str(item['_id']),
            'ownerId': str(self.user['_id'])
        })
        self.assertStatusOk(resp)
        lockId = resp.json['_id']

        resp = self.request('/dm/lock', method='GET', user=self.user, params={
            'sessionId': sessionId
        })
        self.assertStatusOk(resp)
        locks = resp.json
        self.assertEqual(len(locks), 1)

        # test list locks with params
        resp = self.request('/dm/lock', method='GET', user=self.user, params={
            'sessionId': sessionId,
            'itemId': str(item['_id']),
            'ownerId': str(self.user['_id'])
        })
        self.assertStatusOk(resp)

        # test list locks for session
        resp = self.request('/dm/session/%s/lock' % sessionId, method='GET', user=self.user)
        self.assertStatusOk(resp)

        # test get lock
        resp = self.request('/dm/lock/%s' % lockId, method='GET', user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(lockId, str(resp.json['_id']))

        item = self.reloadItemRest(item)
        self.assertHasKeys(item, ['dm'])

        psPath = self.waitForFile(item, rest=True, sessionId=sessionId)
        shouldHaveBeenTransferred = psPath in self.transferredFiles
        self.transferredFiles.add(psPath)

        resp = self.request('/dm/transfer', method='GET', user=self.user, params={
            'sessionId': sessionId,
            'discardOld': 'false'
        })
        self.assertStatusOk(resp)
        transfers = resp.json
        self.assertEqual(len(transfers), len(self.transferredFiles))

        # test list transfers for session
        resp = self.request('/dm/session/%s/transfer' % sessionId, method='GET', user=self.user)
        self.assertStatusOk(resp)
        transfers = resp.json
        if shouldHaveBeenTransferred:
            self.assertEqual(len(transfers), 1)
        else:
            self.assertEqual(len(transfers), 0)

        self.assertTrue(os.path.isfile(psPath))
        self.assertEqual(os.path.getsize(psPath), item['size'])

        resp = self.request('/dm/lock/%s/download' % lockId, method='GET', user=self.user,
                            isJson=False)
        self.assertStatusOk(resp)
        body = self.getBody(resp, text=False)
        self.assertEqual(len(body), item['size'])

        resp = self.request('/dm/lock/%s' % lockId, method='DELETE', user=self.user)
        self.assertStatusOk(resp)

        item = self.reloadItemRest(item)
        self.assertEqual(item['dm']['lockCount'], 0)

        resp = self.request('/dm/session/%s' % sessionId, method='DELETE', user=self.user)
        self.assertStatusOk(resp)

    def reloadItemRest(self, item):
        resp = self.request('/item/{_id}'.format(**item), method='GET',
                            user=self.user)
        self.assertStatusOk(resp)
        return resp.json

    def test07FileGC(self):
        gc = self.apiroot.dm.getFileGC()
        gc.pause()

        dataSet = self.makeDataSet(self.gfiles)
        self._testItem(dataSet, self.gfiles[0])
        self._testItem(dataSet, self.gfiles[1])

        cachedItems = self._getCachedItems()
        self.assertEqual(2, len(cachedItems))

        files = [x['dm']['psPath'] for x in cachedItems]

        self.model('setting').set('dm.private_storage_capacity', int(2.2 * MB))
        self.model('setting').set('dm.gc_collect_start_fraction', 0.5)  # if over 1.1 MB
        self.model('setting').set('dm.gc_collect_end_fraction', 0.5)   # if under 1.1 MB
        gc._collect()
        # should have cleaned one file
        remainingCount = 0
        for f in files:
            if os.path.exists(f):
                remainingCount += 1

        self.assertEqual(1, remainingCount)
        self.assertEqual(1, len(self._getCachedItems()))
        gc.resume()

    def _getCachedItems(self):
        return list(self.model('item').find({'dm.cached': True}, user=self.user))

    def test08StructureAccess(self):
        # mount the root collection and try to lock files
        dataSet = self.makeDataSet([{'_id': self.testFolder['_id'], 'name': 'fldr'}],
                                   objectids=False)

        resp = self.request('/dm/session', method='POST', user=self.user, params={
            'dataSet': json.dumps(dataSet)
        })
        self.assertStatusOk(resp)
        sessionId = resp.json['_id']

        item = self.gfiles[0]

        resp = self.request('/dm/lock', method='POST', user=self.user, params={
            'sessionId': sessionId,
            'itemId': str(item['_id']),
            'ownerId': str(self.user['_id'])
        })
        self.assertStatusOk(resp)
        lockId = resp.json['_id']

        resp = self.request('/dm/lock/%s' % lockId, method='DELETE', user=self.user)
        self.assertStatusOk(resp)

        item = self.reloadItemRest(item)
        self.assertEqual(item['dm']['lockCount'], 0)

        item2 = self.gfiles2[0]

        resp = self.request('/dm/lock', method='POST', user=self.user, params={
            'sessionId': sessionId,
            'itemId': str(item2['_id']),
            'ownerId': str(self.user['_id'])
        })
        # not in the collection
        self.assertStatus(resp, 404)

    def test09TaleUpdateEventHandler(self):
        dataSet = self.makeDataSet([{'_id': self.testFolder['_id'], 'name': 'fldr'}],
                                   objectids=False)
        dataSet[0]["_modelType"] = "folder"
        from girder.plugins.wholetale.models.tale import Tale
        tale = Tale().createTale({'_id': ObjectId()}, dataSet, title='test09',
                                 creator=self.user)

        resp = self.request(
            path='/dm/session', method='POST', user=self.user,
            params={'taleId': str(tale['_id'])}
        )
        self.assertStatusOk(resp)
        session = resp.json
        self.assertEqual(session['dataSet'], dataSet)

        tale['dataSet'].pop(0)
        tale = Tale().save(tale)
        resp = self.request(
            path='/dm/session/{_id}'.format(**session), method='GET',
            user=self.user
        )
        self.assertStatusOk(resp)
        session = resp.json
        self.assertEqual(session['dataSet'], tale['dataSet'])

        Tale().remove(tale)  # TODO: This should fail, since the session is up
        resp = self.request(
            path='/dm/session/{_id}'.format(**session),
            method='DELETE', user=self.user)
        self.assertStatusOk(resp)
