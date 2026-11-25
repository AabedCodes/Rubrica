"""Handoff between the ingestion worker and the isolated parser."""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

_MAX_INPUT_BYTES = 10_000_000
_EXTENSIONS = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


def stage_input(inbox: Path, job_id: UUID, content_type: str, content: bytes) -> None:
    if content_type not in _EXTENSIONS:
        raise ValueError("Unsupported parser input type")
    if len(content) > _MAX_INPUT_BYTES:
        raise ValueError("Parser input too large")

    destination = inbox / f"{job_id}{_EXTENSIONS[content_type]}"
    with NamedTemporaryFile(dir=inbox, suffix=".tmp", delete=False) as pending:
        temporary = Path(pending.name)
        try:
            pending.write(content)
        except OSError:
            pending.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def read_result(outbox: Path, job_id: UUID) -> dict | None:
    try:
        contents = (outbox / f"{job_id}.json").read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    return json.loads(contents)
