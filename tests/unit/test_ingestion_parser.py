from pathlib import Path
from uuid import UUID

from pypdf import PdfWriter

from backend.ingestion.exchange import read_result, stage_input
from backend.ingestion.parser import parse_file, parse_pending

FIXTURE = Path(__file__).parents[2] / "seed" / "canaries" / "T04.pdf"


def test_pdf_fixture_preserves_hidden_text_for_review():
    result = parse_file(FIXTURE)
    assert result["pages"] == 1
    assert result["has_text_layer"]
    assert "CANARY-T04-772d" in result["text"]


def test_blank_pdf_is_rejected_as_scanned(tmp_path):
    file = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(str(file))
    assert parse_file(file) == {
        "error": "scanned_document",
        "pages": 1,
        "has_text_layer": False,
    }


def test_volume_worker_processes_a_job_once(tmp_path):
    inbox, outbox = tmp_path / "in", tmp_path / "out"
    inbox.mkdir()
    outbox.mkdir()
    job = UUID(int=1)
    stage_input(inbox, job, "text/markdown", b"Example markdown")
    assert read_result(outbox, job) is None
    (inbox / "not-a-job.md").write_text("Ignored", encoding="utf-8")
    heartbeat = tmp_path / "heartbeat"

    parse_pending(inbox, outbox, heartbeat, 5)

    result = outbox / f"{job}.json"
    assert read_result(outbox, job) == {
        "text": "Example markdown",
        "pages": 1,
        "has_text_layer": True,
    }
    timestamp = result.stat().st_mtime_ns
    parse_pending(inbox, outbox, heartbeat, 5)
    assert list(outbox.iterdir()) == [result]
    assert result.stat().st_mtime_ns == timestamp
