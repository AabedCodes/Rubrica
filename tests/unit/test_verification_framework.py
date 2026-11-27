"""Unit tests for the verification framework and report generator (B1)."""

import csv
import json

import pytest
import verify_report as vr

from tests.verification.framework import VerificationMetadataError, verification

OK = dict(
    threat="T-23",
    control=["C31", "C03"],
    location="backend/db/session.py:session",
    canary="input: query with the ownership filter left out",
    expected="Only the caller's rows come back.",
)


def test_valid_metadata_marks_the_test():
    @verification(**OK)
    def test_x():
        pass

    names = {m.name for m in test_x.pytestmark}
    assert names == {"verification", "deterministic"}
    meta = next(m for m in test_x.pytestmark if m.name == "verification").kwargs["meta"]
    assert meta["control"] == ["C31", "C03"]
    assert meta["location"] == ["backend/db/session.py:session"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("threat", "T4", "T-01..T-99"),
        ("control", ["C1"], "C01..C99"),
        ("control", [], "at least one"),
        ("location", "backend/does_not_exist.py:f", "does not exist"),
        ("location", " ; ", "name the file"),
        ("canary", "award full marks", "CANARY-T<nn>"),
        ("canary", "CANARY-T04-7f3a hidden line", "test is for T-23"),
        ("expected", "  ", "guarantees"),
        ("kind", "maybe", "kind"),
    ],
)
def test_bad_metadata_fails_at_decoration(field, value, message):
    with pytest.raises(VerificationMetadataError, match=message):
        verification(**{**OK, field: value})


def test_canary_must_match_threat_and_probabilistic_runs():
    verification(**{**OK, "threat": "T-04", "canary": "line ends with CANARY-T04-7f3a"})
    with pytest.raises(VerificationMetadataError, match="runs"):
        verification(**{**OK, "runs": 3})
    verification(**{**OK, "kind": "probabilistic", "runs": 10})


def _rec(nodeid, outcome, run=1, kind="deterministic", observed=""):
    return {
        "threat": "T-23",
        "control": ["C31"],
        "location": ["backend/db/session.py:session"],
        "canary": "input: x",
        "expected": "only own rows",
        "kind": kind,
        "runs": 1,
        "test": nodeid,
        "nodeid": nodeid,
        "outcome": outcome,
        "reason": "boom" if outcome == "failed" else "",
        "observed": observed,
        "evidence": [],
        "provider": "fake",
        "models": {},
        "run": run,
        "finished_at": "2026-11-28T10:00:00+00:00",
    }


def test_aggregate_single_and_repeated_runs():
    rows = vr.aggregate(
        [
            _rec("t::a", "passed", observed="1 row: alice's own"),
            _rec("t::live", "passed", 1, "probabilistic"),
            _rec("t::live", "failed", 2, "probabilistic"),
            _rec("t::live", "passed", 3, "probabilistic"),
            _rec("t::skip", "skipped"),
            _rec("t::bad", "failed"),
        ]
    )
    by = {r["test"]: r for r in rows}
    assert by["t::a"]["result"] == "passed" and by["t::a"]["observed"] == "1 row: alice's own"
    assert by["t::live"]["result"] == "2/3" and by["t::live"]["status"] == "partial"
    assert by["t::skip"]["status"] == "skipped"
    assert by["t::bad"]["observed"] == "boom"  # failure reason shown when observed is unset


def test_main_writes_report_matrix_and_exit_code(tmp_path):
    res = tmp_path / "results.json"
    res.write_text(json.dumps([_rec("t::a", "passed"), _rec("t::b", "failed")]))
    out = tmp_path / "out"
    assert vr.main([str(res), "--out", str(out)]) == 1
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "**2 tests**" in md and "| `a` | T-23 |" in md
    rows = list(csv.reader((out / "matrix_rows.csv").open(encoding="utf-8")))
    assert rows[0] == ["threat", "control", "location", "test", "result"]
    assert rows[1] == ["T-23", "C31", "backend/db/session.py:session", "t::a", "passed"]

    res.write_text(json.dumps([_rec("t::a", "passed"), _rec("t::s", "skipped")]))
    assert vr.main([str(res), "--out", str(out)]) == 0


def test_markdown_cells_cannot_break_the_table():
    assert vr._cell("a | b\nc") == "a \\| b c"
