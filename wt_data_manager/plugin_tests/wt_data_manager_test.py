#!/usr/bin/env python
# -*- coding: utf-8 -*-


from tests import base
import tempfile
import time
import os


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
        print(self.gfiles)

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

    def testLocalFile(self):
        dataSet = [{'itemId': f['_id'], 'mountPoint': '/' + f['name']} for f in self.gfiles]
        session = self.model('session', 'wt_data_manager').createSession(self.user, dataSet=dataSet)
        self.assertNotEqual(session, None)
        item = self.gfiles[0]
        self.assertNotHasKeys(item, ['dm'])
        lock = self.model('lock', 'wt_data_manager').acquireLock(self.user, session['_id'],
                                                                 item['_id'])
        self.assertNotEqual(lock, None)

        item = self.reloadItem(item)
        self.assertHasKeys(item, ['dm'])

        psPath = self.waitForFile(item)

        self.assertTrue(os.path.isfile(psPath))
        self.assertEqual(os.path.getsize(psPath), item['size'])

        self.model('lock', 'wt_data_manager').releaseLock(self.user, lock)

        item = self.reloadItem(item)
        self.assertEqual(item['dm']['lockCount'], 0)

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
