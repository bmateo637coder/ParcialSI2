"""Ejecuta la verificación de navegador con servidores y datos temporales."""
import functools
import http.server
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    mobile = '--mobile' in sys.argv
    workspace = Path(__file__).resolve().parents[2]
    backend = workspace / "backend"
    webroot = workspace / "frontend-web/browser/browser"
    if not mobile and not (webroot / "index.html").exists():
        raise SystemExit("Primero ejecuta npm run build en frontend-web.")
    api_port, web_port = free_port(), free_port()

    class SPAHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            requested = self.path.split("?")[0]
            if not (webroot / requested.lstrip("/")).is_file():
                self.path = "/index.html"
            super().do_GET()

        def log_message(self, *args):
            pass

    folder = tempfile.TemporaryDirectory(prefix="fashionstore_browser_check_")
    root = Path(folder.name).resolve()
    assert root.parent == Path(tempfile.gettempdir()).resolve()
    assert root.name.startswith("fashionstore_browser_check_")
    env = dict(os.environ, DATABASE_URL="sqlite:///" + str(root / "browser.db"),
        SECRET_KEY="browser-test-secret", AUTO_SEED="false", GENAI_API_KEY="",
        BACKEND_CORS_ORIGINS=f'["http://127.0.0.1:{web_port}"]')
    server = process = log = None
    try:
        seed = subprocess.run([sys.executable, "-X", "utf8", "seed.py"], cwd=backend,
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if seed.returncode:
            raise RuntimeError(seed.stderr[-4000:])
        log = (root / "backend.log").open("w", encoding="utf-8")
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(api_port)],
            cwd=backend, env=env, stdout=log, stderr=log, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(150):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{api_port}/api/health", timeout=1).close()
                break
            except Exception:
                if process.poll() is not None:
                    raise RuntimeError((root / "backend.log").read_text()[-4000:])
                time.sleep(0.2)
        else:
            raise RuntimeError("El backend temporal no inició a tiempo")
        if mobile:
            mobile_env = dict(os.environ, MOBILE_E2E_API_URL=f"http://127.0.0.1:{api_port}/api")
            print("Verificando Flutter y SQLite con backend temporal real.", flush=True)
            result = subprocess.run(["flutter.bat" if os.name == 'nt' else 'flutter', "test", "--no-pub", "--concurrency=1"],
                cwd=workspace / 'movil', env=mobile_env)
        else:
            server = http.server.ThreadingHTTPServer(("127.0.0.1", web_port), functools.partial(SPAHandler, directory=str(webroot)))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            node_env = dict(os.environ, E2E_WEB_URL=f"http://127.0.0.1:{web_port}", E2E_API_URL=f"http://127.0.0.1:{api_port}/api")
            print("Verificando PWA con Chromium y backend temporal.", flush=True)
            script = 'refund-check.cjs' if '--refunds' in sys.argv else 'shop-check.cjs' if '--shop' in sys.argv else 'offline-check.cjs'
            result = subprocess.run(["node", str(workspace / "frontend-web/e2e" / script)], cwd=workspace, env=node_env)
        if result.returncode:
            log.flush()
            print((root / 'backend.log').read_text(encoding='utf-8')[-4000:])
        return result.returncode
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if process and process.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                process.terminate()
            process.wait(timeout=10)
        if log:
            log.close()
        folder.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
