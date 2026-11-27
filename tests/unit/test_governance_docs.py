"""Checks on the A10 governance documents: links resolve, and every control has a status.

The system card must not claim a control that isn't built (A10), so each row of
its controls table carries a status of Built, In review or Planned.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DOCS = [ROOT / "docs" / "system-card.md", ROOT / "docs" / "disclosure.md"]
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
STATUSES = ("Built", "In review", "Planned")


def relative_links(doc: Path) -> list[str]:
    return [
        t
        for t in LINK.findall(doc.read_text(encoding="utf-8"))
        if not re.match(r"^[a-z]+:", t) and not t.startswith("#")
    ]


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.name)
def test_relative_links_point_to_existing_files(doc: Path) -> None:
    missing = [
        t for t in relative_links(doc) if not (doc.parent / t.split("#")[0]).resolve().exists()
    ]
    assert missing == [], f"{doc.name} links to missing files: {missing}"


def _table_after(heading: str, text: str) -> list[list[str]]:
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    return [
        [cell.strip() for cell in row.strip("|").split("|")] for row in rows[2:]
    ]  # skip header and rule


def test_every_control_in_the_system_card_has_a_status() -> None:
    text = DOCS[0].read_text(encoding="utf-8")
    rows = _table_after("## 7. Security controls summary", text)
    assert len(rows) >= 10
    for row in rows:
        assert row[-1].startswith(STATUSES), f"control without a status: {row[0]}"


def test_every_component_has_a_status() -> None:
    text = DOCS[0].read_text(encoding="utf-8")
    rows = _table_after("## 2. Models and components", text)
    for row in rows:
        assert row[1].startswith(STATUSES), f"component without a status: {row[0]}"


def test_no_agent_is_described_as_built() -> None:
    # Guard for this draft: the agents and MCP server are planned, so the card must say so.
    text = DOCS[0].read_text(encoding="utf-8")
    assert "**No agent is built yet.**" in text
