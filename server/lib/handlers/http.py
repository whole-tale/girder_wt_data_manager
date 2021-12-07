import urllib
import zipfile

import httpio
import requests
from .common import FileLikeUrlTransferHandler


# we should probably have a better way of doing this
SCOPE_MAP = {'pbcconsortium.isrd.isi.edu':
                 'https://auth.globus.org/scopes/a77ee64a-fb7f-11e5-810e-8c705ad34f60/deriva_all'}


class Http(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user,
                                            transferManager)
        self.extra_headers = {}
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc in SCOPE_MAP:
            scope = SCOPE_MAP[parsed.netloc]
            if 'otherTokens' in user:
                for token in user['otherTokens']:
                    if token['scope'] == scope:
                        self.extra_headers['Authorization'] = 'Bearer ' + token['access_token']


    def openInputStream(self):
        parsed = urllib.parse.urlparse(self.url)
        if parsed.path and parsed.path.endswith('.zip') and parsed.query:
            qs = urllib.parse.parse_qs(parsed.query)
            path = qs['path'][0]
            fp = httpio.open(urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                                      '', '', '')), headers=self.extra_headers)
            zf = zipfile.ZipFile(fp)
            try:
                return zipfile.Path(zf, path).open(mode="rb")
            except ValueError:
                return zipfile.Path(zf, path).open()
        else:
            resp = requests.get(self.url, stream=True, headers=self.headers)
            resp.raise_for_status()  # Throw an exception in case transfer failed
            return resp.raw
