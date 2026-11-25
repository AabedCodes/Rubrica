"""Isolated file parser for the shared parse-in and parse-out volumes."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

MAX_INPUT_BYTES = 10_000_000
MAX_TEXT_CHARS = 500_000
MAX_PAGES = 300
MIN_PDF_ALNUM_PER_PAGE = 8
JOB_NAME = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.(?:pdf|txt|md)")


def parse_file(path: Path) -> dict:
    """Return parsed content or a fixed error for one supported file."""
    if path.suffix not in {".pdf", ".txt", ".md"}:
        return {"error": "unsupported_type"}

    try:
        with path.open("rb") as source:
            data = source.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            return {"error": "input_too_large"}

        if path.suffix != ".pdf":
            text = data.decode("utf-8-sig")
            if len(text) > MAX_TEXT_CHARS:
                return {"error": "text_too_large"}
            return {"text": text, "pages": 1, "has_text_layer": bool(text.strip())}

        document = PdfReader(BytesIO(data))
        if document.is_encrypted:
            return {"error": "encrypted_pdf"}
        pages = len(document.pages)
        if pages > MAX_PAGES:
            return {"error": "too_many_pages"}

        parts = []
        size = 0
        for page in document.pages:
            text = page.extract_text()
            size += len(text) + 1
            if size > MAX_TEXT_CHARS:
                return {"error": "text_too_large"}
            parts.append(text)

        text = "\n".join(parts)
        if not pages or sum(char.isalnum() for char in text) < pages * MIN_PDF_ALNUM_PER_PAGE:
            return {"error": "scanned_document", "pages": pages, "has_text_layer": False}
        return {"text": text, "pages": pages, "has_text_layer": True}
    except (OSError, UnicodeError, ValueError, PyPdfError, RecursionError):
        return {"error": "invalid_document"}
    except MemoryError:
        return {"error": "parser_memory_limit"}


def _parse_child(path: Path, timeout: float) -> str:
    try:
        child = subprocess.run(  # noqa: S603 (fixed Python executable and module, no shell)
            [sys.executable, "-m", "backend.ingestion.parser", "--file", str(path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            encoding="utf-8",
            timeout=timeout,
        )
        return child.stdout
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "parse_timeout"})
    except subprocess.CalledProcessError:
        return json.dumps({"error": "parser_failure"})


def parse_pending(inbox: Path, outbox: Path, heartbeat: Path, timeout: float) -> None:
    for source in sorted(inbox.iterdir()):
        if not JOB_NAME.fullmatch(source.name) or source.is_symlink() or not source.is_file():
            continue
        target = outbox / f"{source.stem}.json"
        if target.exists():
            continue
        heartbeat.touch()
        output = _parse_child(source, timeout)
        temporary = target.with_suffix(".tmp")
        temporary.write_text(output, encoding="utf-8")
        temporary.replace(target)


def _limit_child_memory() -> None:
    if sys.platform == "linux":
        import resource

        memory = 384 * 1024 * 1024
        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        if hard != resource.RLIM_INFINITY:
            memory = min(memory, hard)
        resource.setrlimit(resource.RLIMIT_AS, (memory, hard))


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--file":
        _limit_child_memory()
        print(json.dumps(parse_file(Path(sys.argv[2]))))
        return

    inbox = Path("/data/parse-in")
    outbox = Path("/data/parse-out")
    heartbeat = Path(os.environ.get("RUBRICA_HEARTBEAT_FILE", "/tmp/heartbeat"))  # noqa: S108
    timeout = float(os.environ.get("PARSE_TIMEOUT_SECONDS", "30"))
    if not 0 < timeout <= 30:
        raise ValueError("Parser timeout must be between 0 and 30 seconds")
    while True:
        heartbeat.touch()
        parse_pending(inbox, outbox, heartbeat, timeout)
        time.sleep(1)


if __name__ == "__main__":
    main()
