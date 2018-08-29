from girder.models.setting import Setting
from ....constants import PluginSettings, GlobusEnvironmentVariables
from girder import logger
import os
import uuid
import subprocess
import threading
import pathlib
import time
from threading import RLock


def _runGCCommand(*args):
    p = subprocess.run(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        msg = 'Command %s failed with exit code %s: \n%s\n%s' % (args, p.returncode, p.stdout,
                                                                 p.stderr)
        logger.warn(msg)
        raise Exception(msg)
    logger.info('Output from command %s: %s, %s' % (args, p.stdout, p.stderr))
    return p


class GCThread(threading.Thread):
    def __init__(self, gcDir, confDir, globusRoot):
        threading.Thread.__init__(self, name='Globus Connect')
        self.daemon = True
        self.gcDir = gcDir
        self.confDir = confDir
        self.globusRoot = globusRoot

    def run(self):
        if not os.path.exists(self.globusRoot):
            os.makedirs(self.globusRoot)
        _runGCCommand('%s/globusconnectpersonal' % self.gcDir, '-start', '-restrict-paths',
                      'rw%s' % self.globusRoot, '-shared-paths', self.globusRoot, '-dir',
                      self.confDir)


class Server:
    def __init__(self, clients):
        self.gcDir = self._getGCDir()
        self.sharedEndpoints = None
        self.sharedEndpointsLock = RLock()
        self.sharedEndpointsCreationLocks = {}
        self.globusRoot = Setting().get(PluginSettings.GLOBUS_ROOT_PATH, '/tmp/wt-globus')
        self.clients = clients

    def start(self):
        # look for an endpoint name, which means that we've previously initialized a personal
        # endpoint
        # allow storing multiple endpoints if there are multiple Globus applications
        key = self._getEndpointKey()
        self.confDir = '%s/.WholeTale/%s' % (pathlib.Path.home(), key)
        (self.endpointId, self.endpointName) = self._getEndpointDataByKey(key)
        if self.endpointId is None:
            (self.endpointId, self.endpointName) = self._createEndpoint()
            self._storeEndpointData(key, self.endpointId, self.endpointName)
        self._startGCServer()

    def _getEndpointKey(self):
        # returns either the Globus app ID or none if a token is being used
        if self.clients.getGlobusAdminToken() is not None:
            return 'default'
        else:
            return self.clients.getGlobusClientId()

    def _getEndpointDataByKey(self, key):
        settings = Setting()
        endpointIds = settings.get(PluginSettings.GLOBUS_ENDPOINT_ID, None)
        endpointNames = settings.get(PluginSettings.GLOBUS_ENDPOINT_NAME, None)
        (endpointIds, endpointNames) = self._maybeConvertSettings(endpointIds, endpointNames)
        if endpointIds is None:
            return (None, None)
        else:
            if key in endpointIds:
                return (endpointIds[key], endpointNames[key])
            else:
                return (None, None)

    def _maybeConvertSettings(self, endpointIds, endpointNames):
        # remove me
        if isinstance(endpointIds, str):
            endpointIds = {None: endpointIds}
            endpointNames = {None: endpointNames}
            settings = Setting()
            settings.set(PluginSettings.GLOBUS_ENDPOINT_ID, endpointIds)
            settings.set(PluginSettings.GLOBUS_ENDPOINT_NAME, endpointNames)
        return (endpointIds, endpointNames)

    def _storeEndpointData(self, key, endpointId, endpointName):
        settings = Setting()
        endpointIds = settings.get(PluginSettings.GLOBUS_ENDPOINT_ID, None)
        endpointNames = settings.get(PluginSettings.GLOBUS_ENDPOINT_NAME, None)
        if endpointIds is None:
            endpointIds = {}
            endpointNames = {}
        endpointIds[key] = endpointId
        endpointNames[key] = endpointName
        settings.set(PluginSettings.GLOBUS_ENDPOINT_ID, endpointIds)
        settings.set(PluginSettings.GLOBUS_ENDPOINT_NAME, endpointNames)

    def _maybeCreateUserEndpoint(self, user):
        userName = user['login']
        lock = None
        create = False
        with self.sharedEndpointsLock:
            self._initSharedEndpoints()
            # check if another thread is creating the EP
            if userName in self.sharedEndpointsCreationLocks:
                lock = self.sharedEndpointsCreationLocks[userName]
            if lock is None:
                if userName in self.sharedEndpoints:
                    return
                else:
                    lock = RLock()
                    lock.acquire()
                    self.sharedEndpointsCreationLocks[userName] = lock
                    create = True

        if not create:
            # wait
            lock.acquire()
        try:
            if create:
                self._createUserEndpoint(user)
        finally:
            lock.release()
            if create:
                del self.sharedEndpointsCreationLocks[userName]

    def _createUserEndpoint(self, user):
        userName = user['login']
        tc = self.clients.getTransferClient()
        fullPath = '%s/%s/' % (self.globusRoot, userName)
        if not os.path.exists(fullPath):
            os.makedirs(fullPath)
        resp = tc.create_shared_endpoint({
            'DATA_TYPE': 'shared_endpoint',
            'host_endpoint': self.endpointId,
            'host_path': '%s' % fullPath,
            'display_name': '%s-%s' % (self.endpointName, userName),
            'description': userName,
        })
        if 'id' not in resp:
            raise Exception('Failed to create user endpoint: %s' % resp)
        id = resp['id']
        self.sharedEndpoints[userName] = resp
        failure = None
        try:
            resp = tc.add_endpoint_acl_rule(resp['id'], {
                'DATA_TYPE': 'access',
                'principal_type': 'identity',
                'principal': self._getGlobusUserId(user),
                # From http://globus-sdk-python.readthedocs.io/en/stable/clients/transfer/:
                # Note that if this rule is being created on a shared endpoint the “path” field is
                # relative to the “host_path” of the shared endpoint
                'path': '/',
                'permissions': 'rw'
            })
            if resp['code'] != 'Created':
                failure = resp
        except Exception as ex:
            # does the API raise exceptions for soft failed calls or just return them? They
            # don't say
            failure = ex
        if failure is not None:
            tc.delete_endpoint(id)
            raise Exception("Could not set ACL rule on shared endpoint for user %s: %s" %
                            (userName, failure))

    def _getGlobusUserId(self, user):
        if 'oauth' in user:
            for entry in user['oauth']:
                if 'provider' in entry and entry['provider'] == 'globus':
                    return entry['id']
        raise Exception('Could not find Globus id for user %s' % user['login'])

    def getUserDir(self, user):
        return '%s/%s' % (self.globusRoot, user['login'])

    def getUserEndpointId(self, user):
        self._maybeCreateUserEndpoint(user)
        with self.sharedEndpointsLock:
            return self.sharedEndpoints[user['login']]['id']

    def _initSharedEndpoints(self):
        if self.sharedEndpoints is not None:
            return
        self.sharedEndpoints = {}
        tc = self.clients.getTransferClient()
        resp = tc.my_shared_endpoint_list(self.endpointId)
        for ep in resp:
            self.sharedEndpoints[ep['description']] = ep

    def _startGCServer(self):
        gcThread = GCThread(self.gcDir, self.confDir, self.globusRoot)
        gcThread.start()
        self._waitForGCServerToConnect()

    def _waitForGCServerToConnect(self):
        tc = self.clients.getTransferClient()
        for attempt in range(20):
            ep = tc.get_endpoint(self.endpointId)
            if ep['gcp_connected']:
                return
            time.sleep(1)

        raise Exception('Globus Connect Server was not reported as connected after 20s')

    def _createEndpoint(self):
        tc = self.clients.getTransferClient()
        endpointName = self._generateEndpointName()

        res = tc.create_endpoint({
            'DATA_TYPE': 'endpoint',
            'display_name': endpointName,
            #'public': False,
            'public': True,
            'is_globus_connect': True,
        })
        endpointId = res['id']
        setupKey = res['globus_connect_setup_key']
        _runGCCommand('%s/globusconnectpersonal' % self.gcDir, '-setup', setupKey, '-dir',
                      self.confDir)

        return (endpointId, endpointName)

    def _generateEndpointName(self):
        return 'wt-%s' % uuid.uuid4()

    def _getGCDir(self):
        return self.clients._getGlobusSetting(GlobusEnvironmentVariables.GLOBUS_CONNECT_DIR,
                                              PluginSettings.GLOBUS_CONNECT_DIR)
