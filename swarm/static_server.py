#!/usr/bin/env python3
"""FRACTALMESH v10332.2 Static server serving web/ + public/ from this repo dir."""
import os, http.server, socketserver, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | STATIC | %(levelname)s | %(message)s")
logger = logging.getLogger("Static")

PORT = int(os.getenv("STATIC_PORT", "7790"))
ROOT = os.path.dirname(os.path.abspath(__file__))  # swarm/
WEBROOT = os.path.abspath(os.path.join(ROOT, "..", "web"))


class MultiRootHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Try the web/ dir first, then repo root (public/).
        p = super().translate_path(path)
        rel = os.path.relpath(p, self.directory)
        p1 = os.path.join(ROOT, "..", "web", rel)
        if os.path.isfile(p1) or os.path.isdir(p1):
            return p1
        return super().translate_path(path)

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, fmt, *args):
        logger.info(fmt % args)


def run():
    with socketserver.TCPServer(("0.0.0.0", PORT), MultiRootHandler) as httpd:
        logger.info("[+] Static server on :%d (web/ + public/)", PORT)
        httpd.serve_forever()


if __name__ == "__main__":
    run()
