"""Placeholder service so `make up` works before each owner's service exists.

Usage: python -m backend.common.placeholder <service-name>

Serves GET /healthz on $PORT (default 8000). With RUBRICA_NO_NETWORK=1 (the
parser, which has no network at all) it only touches a heartbeat file.
Each owner replaces their service's `command:` in deploy/docker-compose.yml
with the real entry point; delete this module once none uses it.
"""

from __future__ import annotations

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HEARTBEAT = Path(os.environ.get("RUBRICA_HEARTBEAT_FILE", "/tmp/heartbeat"))  # noqa: S108


def serve_health(name: str, port: int) -> None:
    body = json.dumps({"status": "ok", "service": name, "placeholder": True}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            if self.path != "/healthz":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            pass  # healthchecks every few seconds would flood the logs

    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()  # noqa: S104 (container)


def heartbeat_forever() -> None:
    while True:
        HEARTBEAT.touch()
        time.sleep(5)


def main(argv: list[str]) -> int:
    name = argv[0] if argv else "unknown"
    print(f"{name}: placeholder service running (replace with the real entry point)", flush=True)
    if os.environ.get("RUBRICA_NO_NETWORK") == "1":
        heartbeat_forever()
    else:
        serve_health(name, int(os.environ.get("PORT", "8000")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
