"""Sirve la compilación web y conecta /api con el backend de esta PC."""
import argparse
import http.client
import http.server
from pathlib import Path
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=4200)
parser.add_argument('--api-port', type=int, default=8001)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / 'browser' / 'browser'
if not (root / 'index.html').is_file():
    raise SystemExit('Ejecuta npm run build antes de iniciar la web.')


class LocalHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *values, **kwargs):
        super().__init__(*values, directory=str(root), **kwargs)

    def do_GET(self):
        requested = urlsplit(self.path).path
        if requested == '/api' or requested.startswith('/api/'):
            return self.proxy()
        if not (root / requested.lstrip('/')).is_file():
            self.path = '/index.html'
        super().do_GET()

    def proxy(self):
        if not (self.path == '/api' or self.path.startswith('/api/')):
            return self.send_error(404)
        connection = http.client.HTTPConnection('127.0.0.1', args.api_port, timeout=25)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length) if length else None
            headers = {key: value for key, value in self.headers.items()
                if key.lower() not in {'host', 'connection', 'accept-encoding'}}
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in {'connection', 'content-length', 'transfer-encoding'}:
                    self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (OSError, http.client.HTTPException):
            self.send_error(502, 'El backend local no esta disponible')
        finally:
            connection.close()

    do_POST = proxy
    do_PATCH = proxy
    do_PUT = proxy
    do_DELETE = proxy
    do_OPTIONS = proxy


print(f'FashionStore: http://localhost:{args.port}', flush=True)
http.server.ThreadingHTTPServer(('127.0.0.1', args.port), LocalHandler).serve_forever()
