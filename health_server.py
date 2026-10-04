"""
Minimal HTTP health server for Render / Railway Web Services.
Binds to $PORT so platform health checks pass.
Telegram bot runs separately — this only answers GET / with 200 OK.
"""
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Renu Music OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[health] listening on 0.0.0.0:{port}")
    return server


if __name__ == "__main__":
    start_health_server()
    threading.Event().wait()
