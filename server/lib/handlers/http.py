import functools
import urllib
import zipfile

import httpio
import requests

from .common import FileLikeUrlTransferHandler


class Http(FileLikeUrlTransferHandler):
    def openInputStream(self):
        parsed = urllib.parse.urlparse(self.url)
        if parsed.path and parsed.path.endswith('.zip') and parsed.query:
            qs = urllib.parse.parse_qs(parsed.query)
            path = qs['path'][0]
            fp = httpio.open(urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                                      '', '', '')), headers=self.headers)
            zf = zipfile.ZipFile(fp)
            try:
                return zipfile.Path(zf, path).open(mode="rb")
            except ValueError:
                return zipfile.Path(zf, path).open()
        else:
            resp = requests.get(self.url, stream=True, headers=self.headers)
            if resp.headers.get("Content-Encoding") in ("gzip",):
                resp.raw.read = functools.partial(resp.raw.read, decode_content=True)
            resp.raise_for_status()  # Throw an exception in case transfer failed
            return resp.raw
