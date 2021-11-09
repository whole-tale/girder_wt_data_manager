import urllib
import zipfile

import httpio
import requests
from .common import FileLikeUrlTransferHandler


class Http(FileLikeUrlTransferHandler):
    def __init__(self, url, transferId, itemId, psPath, user, transferManager):
        FileLikeUrlTransferHandler.__init__(self, url, transferId, itemId, psPath, user,
                                            transferManager)

    def openInputStream(self):
        parsed = urllib.parse.urlparse(self.url)
        if parsed.path and parsed.path.endswith('.zip') and parsed.query:
            qs = urllib.parse.parse_qs(parsed.query)
            path = qs['path'][0]
            fp = httpio.open(urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                                      '', '', '')))
            zf = zipfile.ZipFile(fp)
            return zipfile.Path(zf, path).open()
        else:
            resp = requests.get(self.url, stream=True, headers=self.headers)
            resp.raise_for_status()  # Throw an exception in case transfer failed
            return resp.raw
