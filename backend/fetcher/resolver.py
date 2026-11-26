"""Resolve public citation hostnames for the egress-isolated fetcher."""

import json
import re
import socket
from http.client import HTTPConnection, HTTPException
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from urllib.parse import quote, unquote

_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
_MAX_RECORDS = 64


def _resolve(host: str) -> tuple[str, ...]:
    labels = host.rstrip(".").split(".")
    if len(host) > 253 or not all(_LABEL.fullmatch(label) for label in labels):
        raise ValueError("Invalid public DNS hostname")
    records = socket.getaddrinfo(
        host,
        443,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    answers = tuple(sorted({str(ip_address(record[4][0])) for record in records}))
    if not 0 < len(answers) <= _MAX_RECORDS:
        raise ValueError("Invalid DNS answer count")
    return answers


def resolve_for_fetcher(host: str, port: int) -> tuple[str, ...]:
    # Literal addresses still pass the caller's public-address policy.
    try:
        return (str(ip_address(host)),)
    except ValueError:
        pass

    conn = HTTPConnection("web-dns", 8000, timeout=3)
    try:
        conn.request("GET", f"/resolve/{quote(host, safe='')}")
        with conn.getresponse() as reply:
            if reply.status != 200:
                raise OSError("Citation DNS failed")
            payload = json.loads(reply.read(4097))
    except (HTTPException, ValueError) as exc:
        raise OSError("Citation DNS failed") from exc
    finally:
        conn.close()
    if (
        not isinstance(payload, list)
        or not 0 < len(payload) <= _MAX_RECORDS
        or not all(isinstance(value, str) for value in payload)
    ):
        raise OSError("Invalid citation DNS reply")
    try:
        return tuple(str(ip_address(value)) for value in payload)
    except ValueError as exc:
        raise OSError("Invalid citation DNS reply") from exc


class _Handler(BaseHTTPRequestHandler):
    def setup(self) -> None:
        self.request.settimeout(4)
        super().setup()

    def log_message(self, _format, *_args) -> None:
        return

    def _reply(self, status: int, payload) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._reply(200, {"status": "ok"})
            return
        if not self.path.startswith("/resolve/") or len(self.path) > 270:
            self._reply(404, {"error": "not_found"})
            return
        try:
            records = _resolve(unquote(self.path.removeprefix("/resolve/")))
        except (OSError, ValueError):
            self._reply(404, {"error": "dns_failure"})
        else:
            self._reply(200, records)


def main() -> None:
    with ThreadingHTTPServer(("0.0.0.0", 8000), _Handler) as server:  # noqa: S104 (Compose service)
        server.serve_forever()


if __name__ == "__main__":
    main()
