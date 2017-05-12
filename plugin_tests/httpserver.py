from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import re
import threading


MULTIPLIERS = {
    '': 1,
    'K': 1024,
    'M': 1024 * 1024,
    'G': 1024 * 1024 * 1024
}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            szMatch = re.search('[0-9]+', self.path)
            if not szMatch:
                raise IOError('size pattern not found')

            szStr = szMatch.group()
            unit = self.path[len(szStr) + 1:]
            sz = int(szStr)

            if unit not in MULTIPLIERS:
                raise IOError('no such unit %s' % unit)
            multiplier = MULTIPLIERS[unit]

            szm = sz * multiplier

            print('Got request for %s x %s (%s)' % (sz, unit, szm))
            mimetype = 'application/octet-stream'

            self.send_response(200)
            self.send_header('Content-type', mimetype)
            self.end_headers()
            for i in range(szm):
                self.wfile.write(chr(i % 256))
            return

        except IOError as ex:
            self.send_error(404, 'File Not Found: %s (%s)' % (self.path, ex.message))


class Server(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, name='HTTP Fake Data Server')
        self.daemon = True

    def start(self):
        self.server = HTTPServer(('', 0), Handler)
        print('Started httpserver on port %s' % self.server.server_port)
        threading.Thread.start(self)

    def run(self):
        try:
            self.server.serve_forever()
        except:
            self.server.socket.close()

    def getUrl(self):
        return 'http://localhost:%s' % self.server.server_port

    def stop(self):
        self.server.shutdown()
