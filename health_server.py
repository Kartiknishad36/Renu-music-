"""
HTTP health server for Render Web Service.
Binds 0.0.0.0:$PORT so platform does not kill the service.
"""
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

_server = None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b"Renu Music OK\n")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return


def start_health_server():
    """Start daemon HTTP server on $PORT (default 10000)."""
    global _server
    port = int(os.environ.get("PORT") or os.environ.get("RENDER_PORT") or "10000")
    try:
        _server = HTTPServer(("0.0.0.0", port), _Handler)
        t = threading.Thread(target=_server.serve_forever, name="health", daemon=True)
        t.start()
        print(f"[health] listening on 0.0.0.0:{port}")
        return _server
    except OSError as e:
        print(f"[health] bind failed port={port}: {e}")
        return None


if __name__ == "__main__":
    start_health_server()
    threading.Event().wait()
