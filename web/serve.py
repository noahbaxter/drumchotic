"""Serve the explorer locally and reload the browser on changes.

template.html edits show on the next reload straight away. Edits to build.py, the drumchotic
package or the feature caches rebuild the data first (about a minute), then reload.

python -m web.serve [port]
"""
import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import build

ROOT = Path(__file__).resolve().parent.parent
POLL_S = 1.0
# polls the server and reloads when the page or its data changed; shows a badge while rebuilding
RELOAD = """<div id="__dev" style="position:fixed;right:12px;bottom:12px;padding:4px 10px;border-radius:6px;
background:#2a2a28;color:#c3c2b7;font:12px system-ui;display:none">rebuilding data...</div>
<script>(() => { let v = null;
  setInterval(async () => { try {
    const s = await (await fetch('/__version')).json();
    document.getElementById('__dev').style.display = s.building ? 'block' : 'none';
    if (v !== null && s.v !== v) location.reload(); v = s.v; } catch (e) {} }, 1000); })();</script>
</body>"""


def data_inputs():
    return [build.__file__, *ROOT.glob('drumchotic/**/*.py'), *ROOT.glob('data/cache/features*.json')]


def stamp(paths):
    return max((Path(p).stat().st_mtime for p in paths if Path(p).exists()), default=0)


class State:
    building = False


def rebuild_when_inputs_change():
    seen = stamp(data_inputs())
    while True:
        time.sleep(POLL_S)
        now = stamp(data_inputs())
        if now == seen:
            continue
        seen = now
        State.building = True
        print('inputs changed, rebuilding data...', flush=True)
        done = subprocess.run([sys.executable, '-m', 'web.build'], cwd=ROOT, capture_output=True, text=True)
        print(done.stderr[-2000:] if done.returncode else 'rebuilt', flush=True)
        State.building = False


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/__version':
            v = f'{stamp([build.TEMPLATE])}-{stamp([build.DATA])}'
            self.send(json.dumps({'v': v, 'building': State.building}), 'application/json')
        elif self.path.split('?')[0] in ('/', '/index.html'):
            self.send(build.page().replace('</body>', RELOAD, 1), 'text/html')
        else:
            self.send_error(404)

    def send(self, text, kind):
        body = text.encode()
        self.send_response(200)
        self.send_header('Content-Type', f'{kind}; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def main(argv):
    port = int(argv[0]) if argv else 8781
    if not build.DATA.exists():
        print('no data yet, building (about a minute)...', flush=True)
        build.build()
    threading.Thread(target=rebuild_when_inputs_change, daemon=True).start()
    print(f'http://localhost:{port}/  (ctrl-c to stop)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', port), Handler).serve_forever()


if __name__ == '__main__':
    main(sys.argv[1:])
