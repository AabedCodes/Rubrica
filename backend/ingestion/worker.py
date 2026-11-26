"""Lease ingestion jobs and index material or blog text."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from sqlalchemy import and_, or_, select, text

from backend.db import SessionContext, session
from backend.db.models import Job
from backend.ingestion.exchange import read_result, stage_input
from backend.ingestion.index_blog import index_blog
from backend.ingestion.index_material import index_material
from backend.ingestion.parser import MAX_INPUT_BYTES
from backend.retrieval.embedding import load_embedding

_ROLE = "rubrica_ingest"
_UPLOADS = Path("/data/uploads")
_INBOX = Path("/data/parse-in")
_OUTBOX = Path("/data/parse-out")
_MAX_ATTEMPTS = 3
_PARSE_DEADLINE = 120


def claim_job() -> tuple[UUID, str, dict, datetime] | None:
    now = datetime.now(UTC)
    expired = now - timedelta(minutes=5)
    with session(_ROLE, SessionContext("system")) as db:
        job = db.scalar(
            select(Job)
            .where(
                Job.kind.in_(("parse_material", "parse_submission", "index_blog")),
                or_(
                    and_(Job.status == "queued", Job.run_after <= now),
                    and_(Job.status == "parsing", Job.locked_at < expired),
                ),
            )
            .order_by(Job.run_after, Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        if job.attempts >= _MAX_ATTEMPTS:
            job.status = "failed"
            job.locked_at = None
            return None
        job.attempts += 1
        job.status = "parsing"
        job.locked_at = now
        return job.id, job.kind, job.payload, now


def finish_job(job_id: UUID, lease: datetime, status: str) -> bool:
    with session(_ROLE, SessionContext("system")) as db:
        job = db.get(Job, job_id, with_for_update=True)
        if job is None or job.locked_at != lease:
            return False
        job.status = status
        job.locked_at = None
        if status == "queued":
            job.run_after = datetime.now(UTC) + timedelta(seconds=5)
    return True


def _cleanup(job_id: UUID) -> None:
    for suffix in (".pdf", ".txt", ".md"):
        (_INBOX / f"{job_id}{suffix}").unlink(missing_ok=True)
    (_OUTBOX / f"{job_id}.json").unlink(missing_ok=True)


def _store_submission(submission_id: UUID, course_id: UUID, source: bytes, result: dict) -> None:
    parsed = result.get("text")
    if result.get("error") or not isinstance(parsed, str) or not parsed.strip():
        raise ValueError("Parser did not produce usable submission text")
    with session(_ROLE, SessionContext("system", course_id=course_id)) as db:
        stored = db.scalar(
            text("SELECT public.store_parsed_submission(:id, :digest, :contents)"),
            {"id": submission_id, "digest": sha256(source).hexdigest(), "contents": parsed},
        )
        if not stored:
            raise ValueError("Submission source does not match the ingestion job")


def process_job(job_id: UUID, kind: str, payload: dict, embed, heartbeat: Path) -> None:
    course_id = UUID(payload["course_id"])
    if kind == "index_blog":
        index_blog(
            origin=payload["origin"],
            origin_id=UUID(payload["origin_id"]),
            course_id=course_id,
            embed=embed,
        )
        return
    upload_name = str(UUID(payload["upload_id"]))
    upload = _UPLOADS / upload_name
    if upload.is_symlink():
        raise ValueError("Invalid upload reference")
    with upload.open("rb") as file:
        source = file.read(MAX_INPUT_BYTES + 1)
    stage_input(_INBOX, job_id, payload["content_type"], source)
    deadline = time.monotonic() + _PARSE_DEADLINE
    while time.monotonic() < deadline:
        heartbeat.touch()
        result = read_result(_OUTBOX, job_id)
        if result is not None:
            if result.get("error") in {"parse_timeout", "parser_failure", "parser_memory_limit"}:
                raise TimeoutError("Temporary parser failure")
            if kind == "parse_submission":
                _store_submission(UUID(payload["submission_id"]), course_id, source, result)
            else:
                index_material(
                    material_id=UUID(payload["material_id"]),
                    course_id=course_id,
                    source=source,
                    result=result,
                    embed=embed,
                )
            return
        time.sleep(1)
    raise TimeoutError("Parser returned no result")


def main() -> None:
    embed = load_embedding()
    heartbeat = Path(os.environ.get("RUBRICA_HEARTBEAT_FILE", "/tmp/heartbeat"))  # noqa: S108
    while True:
        heartbeat.touch()
        claim = claim_job()
        if claim is None:
            time.sleep(1)
            continue
        job_id, kind, payload, lease = claim
        try:
            process_job(job_id, kind, payload, embed, heartbeat)
        except TimeoutError:
            status = "queued"
        except (KeyError, TypeError, ValueError, FileNotFoundError):
            status = "failed"
        else:
            status = "done"
        if finish_job(job_id, lease, status):
            _cleanup(job_id)


if __name__ == "__main__":
    main()
