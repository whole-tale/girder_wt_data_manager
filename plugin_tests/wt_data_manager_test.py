#!/usr/bin/env python
# -*- coding: utf-8 -*-


from tests import base
import tempfile
import time
import os
import cherrypy


def setUpModule():
    base.enabledPlugins.append('wt_data_manager')
    base.startServer()


def tearDownModule():
    base.stopServer()


class IntegrationTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        self.user = self.model('user').createUser('wt-dm-test-user', 'password', 'Joe', 'User',
                                                  'juser@example.com')
        self.testCollection = \
            self.model('collection').createCollection('wt_dm_test_col', creator=self.user,
                                                      public=False, reuseExisting=True)
        self.testFolder = \
            self.model('folder').createFolder(self.testCollection, 'wt_dm_test_fldr',
                                              parentType='collection')

        self.tmpdir = tempfile.mkdtemp()
        self.files = [self.createFile(n, 1024 * 1024 * n, self.tmpdir) for n in range(1, 5)]
        self.assetstore = list(self.model('assetstore').find({}))[0]
        self.model('assetstore').importData(self.assetstore, self.testFolder, 'folder',
                                            {'importPath': self.tmpdir}, {}, self.user,
                                            leafFoldersAsItems=False)
        self.gfiles = [self.model('item').findOne({'name': file}) for file in self.files]

        self.httpItem = self.model('item').createItem('httpitem1', self.user, self.testFolder)
        self.httpItem['size'] = 1048576
        self.httpItem['meta'] = {'phys_path': 'http://ovh.net/files/1Mio.dat', 'size': 1048576}
        self.model('item').save(self.httpItem)

        self.apiroot = cherrypy.tree.apps['/api'].root.v1

    def createFile(self, suffix, size, dir):
        name = 'file' + str(suffix)
        path = dir + '/' + name
        f = open(path, 'w')
        s = ''.join([chr(x) for x in range(256)])
        for i in range(size // 256):
            f.write(s)
        f.close()
        return name

    def tearDown(self):
        base.TestCase.tearDown(self)

    def makeDataSet(self, items):
        return [{'itemId': f['_id'], 'mountPoint': '/' + f['name']} for f in items]

    def test01LocalFile(self):
        dataSet = self.makeDataSet(self.gfiles)
        self._testItem(dataSet, self.gfiles[0], True)

    def test02HttpFile(self):
        dataSet = self.makeDataSet([self.httpItem])
        self._testItem(dataSet, self.httpItem)

    def test03Caching(self):
        dataSet = self.makeDataSet(self.gfiles)
        self._testItem(dataSet, self.gfiles[0])
        self._testItem(dataSet, self.gfiles[0], transferCount=1)
        item = self.reloadItem(self.gfiles[0])
        self.assertEqual(item['dm']['downloadCount'], 1)
        self._testItem(dataSet, self.gfiles[1], transferCount=2)

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
        self.apiroot.dm.deleteSession(self.user, session=session)

    def _testItem(self, dataSet, item, download=False, transferCount=-1):
        session = self.model('session', 'wt_data_manager').createSession(self.user, dataSet=dataSet)
        self._testItemWithSession(session, item, download=download, transferCount=transferCount)
        self.model('session', 'wt_data_manager').deleteSession(self.user, session)

    def _testItemWithSession(self, session, item, download=False, transferCount=-1):
        self.assertNotEqual(session, None)

        lock = self.model('lock', 'wt_data_manager').acquireLock(self.user, session['_id'],
                                                                 item['_id'])

        locks = list(self.model('lock', 'wt_data_manager').listLocks(self.user, session['_id']))
        self.assertEqual(len(locks), 1)

        self.assertNotEqual(lock, None)

        item = self.reloadItem(item)
        self.assertHasKeys(item, ['dm'])

        psPath = self.waitForFile(item)

        if transferCount > 0:
            transfers = self.model('transfer', 'wt_data_manager').list(self.user, discardOld=False)
            transfers = list(transfers)
            self.assertEqual(len(transfers), transferCount)

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

    def waitForFile(self, item):
        max_iters = 100
        while max_iters > 0:
            if 'cached' in item['dm'] and item['dm']['cached']:
                self.assertHasKeys(item['dm'], ['psPath'])
                psPath = item['dm']['psPath']
                self.assertIsNotNone(psPath)
                return psPath
            time.sleep(0.1)
            max_iters -= 1
            item = self.reloadItem(item)
        self.assertTrue(True, 'No file found after about 10s')
