import os
from threading import RLock

from globus_sdk import RefreshTokenAuthorizer, AccessTokenAuthorizer, ConfidentialAppAuthClient, \
    TransferClient, ClientCredentialsAuthorizer

from girder.plugins.oauth.constants import PluginSettings as OAuthPluginSettings
from girder.models.setting import Setting

from ....constants import GlobusEnvironmentVariables

_TRANSFER_SCOPE = 'urn:globus:auth:scope:transfer.api.globus.org:all'
_APP_TOKEN_VALIDITY_MARGIN = 60
_APP_SCOPES = ['urn:globus:auth:scope:transfer.api.globus.org:all']


class Clients:
    def __init__(self):
        self.userClients = {}
        self.userClientsLock = RLock()
        self.transferClient = None
        self.authClient = None

    def getTransferClient(self, check: bool=False):
        if self.transferClient is None:
            authz = self.getAppTransferAuthorizer()
            self.transferClient = TransferClient(authz)
            if check:
                # almost dummy call as a sanity check
                self.transferClient.task_list(num_results=1)

        return self.transferClient

    def getUserTransferClient(self, user):
        username = user['login']
        authz = self.getAuthorizer(user)
        with self.userClientsLock:
            if username not in self.userClients:
                self.userClients[username] = TransferClient(authz)
            return self.userClients[username]

    def getAuthorizer(self, user):
        if 'otherTokens' not in user:
            raise Exception('No transfer token found')

        tokens = user['otherTokens']

        for token in tokens:
            if token['scope'] == _TRANSFER_SCOPE:
                if 'refresh_token' in token and token['refresh_token'] is not None:
                    return RefreshTokenAuthorizer(token['refresh_token'],
                                                  self.getAuthClient())
                else:
                    return AccessTokenAuthorizer(token['access_token'])

        raise Exception('No globus transfer token found')

    def getAuthClient(self):
        if self.authClient is None:
            clientId = self.getGlobusClientId()
            clientSecret = self.getGlobusClientSecret()

            self.authClient = ConfidentialAppAuthClient(clientId, clientSecret)

        return self.authClient

    def getAppTransferAuthorizer(self):
        # mostly for testing/debugging
        adminToken = self.getGlobusAdminToken()
        if adminToken is not None:
            return AccessTokenAuthorizer(adminToken)

        authClient = self.getAuthClient()

        return ClientCredentialsAuthorizer(authClient, _APP_SCOPES)

    def getGlobusAdminToken(self):
        if 'GLOBUS_ADMIN_TOKEN' in os.environ:
            return os.environ['GLOBUS_ADMIN_TOKEN']

    def getGlobusClientId(self):
        return self._getGlobusSetting(GlobusEnvironmentVariables.GLOBUS_CLIENT_ID,
                                      OAuthPluginSettings.GLOBUS_CLIENT_ID)

    def getGlobusClientSecret(self):
        return self._getGlobusSetting(GlobusEnvironmentVariables.GLOBUS_CLIENT_SECRET,
                                      OAuthPluginSettings.GLOBUS_CLIENT_SECRET)

    def _getGlobusSetting(self, envVarName, settingName):
        # allow environment variables to override stored settings. Use carefully since
        # the OAuth plugin does not look at these.
        if envVarName in os.environ:
            return os.environ[envVarName]

        value = Setting().get(settingName, None)
        if value is None:
            raise Exception('Missing configuration setting "%s" (env "%s")' %
                            (settingName, envVarName))
        return value
