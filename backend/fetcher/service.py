"""Internal citation fetch endpoint and scoped snapshot storage."""

import json
import logging
import os
from hmac import compare_digest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import insert, text
from sqlalchemy.exc import SQLAlchemyError

from backend.db import SessionContext, session
from backend.db.models import WebSnapshot
from backend.fetcher.transport import fetch_citation

_ROLE = "rubrica_fetch"
_MAX_REQUEST = 4096
_LOG = logging.getLogger(__name__)
_SCOPE = text("SELECT public.fetch_submission_in_run(:submission)")
_STATUS = {
    "body_too_large": "too_large",
    "content_type": "not_text",
    "timeout": "timeout",
}


def record_citation(url: str, submission: UUID, context: SessionContext) -> dict:
    with session(_ROLE, context) as db:
        if not db.scalar(_SCOPE, {"submission": submission}):
            raise PermissionError("Submission is outside this grading run")

    result = fetch_citation(url)
    status = _STATUS.get(result.reason, result.status)
    snapshot = uuid4()
    with session(_ROLE, context) as db:
        db.execute(
            insert(WebSnapshot.__table__)
            .inline()
            .values(
                id=snapshot,
                submission_id=submission,
                url=url,
                final_url=result.final_url,
                sha256=result.body_hash,
                text=result.text,
                status=status,
            )
        )
    if result.reason:
        _LOG.warning(
            "citation_fetch status=%s reason=%s snapshot_id=%s run_id=%s",
            status,
            result.reason,
            snapshot,
            context.run_id,
        )
    return {"status": status, "snapshot_id": str(snapshot)}


def _handler(service_key: bytes) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def setup(self) -> None:
            self.request.settimeout(12)
            super().setup()

        def log_message(self, _format, *_args) -> None:
            # Request paths and headers may contain untrusted data.
            return

        def _reply(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._reply(200, {"status": "ok", "service": "fetcher"})
            else:
                self._reply(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if self.path != "/internal/fetch":
                self._reply(404, {"error": "not_found"})
                return
            supplied = self.headers.get("X-Service-Auth", "").encode("utf-8")
            if not compare_digest(service_key, supplied):
                self._reply(403, {"error": "forbidden"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= _MAX_REQUEST or self.headers.get("Transfer-Encoding"):
                    raise ValueError
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict) or set(payload) != {"submission_id", "url"}:
                    raise ValueError
                url = payload["url"]
                if not isinstance(url, str) or not 0 < len(url) <= 2048 or "\x00" in url:
                    raise ValueError
                url.encode("utf-8")
                submission = UUID(payload["submission_id"])
                context = SessionContext(
                    "grading_run",
                    run_id=UUID(self.headers.get("X-Run-Id", "")),
                    course_id=UUID(self.headers.get("X-Course-Id", "")),
                )
            except (ValueError, TypeError, AttributeError, TimeoutError):
                self._reply(400, {"error": "invalid_request"})
                return

            try:
                result = record_citation(url, submission, context)
            except PermissionError:
                self._reply(403, {"error": "forbidden"})
            except SQLAlchemyError:
                self._reply(503, {"error": "fetcher_unavailable"})
            else:
                self._reply(200, result)

    return Handler


def main() -> None:
    secret = Path("/run/secrets/service_auth_grading_agent").read_bytes().rstrip(b"\r\n")
    if not secret:
        raise ValueError("Missing grading service authentication")
    with ThreadingHTTPServer(
        ("0.0.0.0", int(os.environ.get("PORT", "8000"))),  # noqa: S104 (Compose service)
        _handler(secret),
    ) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
