"""Unit tests for scripts/check_coverage.py and scripts/export_threats.py (B8)."""

import json

import check_coverage as cc
import export_threats as et

THREATS = {
    "T-01": {"id": "T-01", "threat": "Key leak", "level": "Critical"},
    "T-23": {"id": "T-23", "threat": "Missing filter", "level": "High"},
    "T-35": {"id": "T-35", "threat": "Regrade promise", "level": "Medium"},
}


def meta(threat, control=("C31",), name="test_x"):
    return {"threat": threat, "control": list(control), "test": f"mod.{threat}::{name}"}


def test_required_threat_without_test_is_a_gap_medium_is_not():
    rows, gaps, errors = cc.check(THREATS, [meta("T-23")], {"T-01": ["C"]})
    assert [g["threat"] for g in gaps] == ["T-01"]
    assert gaps[0]["owners"] == ["C"]
    assert errors == []


def test_unknown_threat_and_control_are_errors():
    _, _, errors = cc.check(THREATS, [meta("T-99"), meta("T-23", ("C38",))], {})
    assert any("T-99" in e for e in errors) and any("C38" in e for e in errors)


def test_with_results_only_passing_tests_count(tmp_path):
    res = tmp_path / "r.json"
    res.write_text(
        json.dumps(
            [
                {"threat": "T-01", "test": "test_T01_x::test_x", "outcome": "failed"},
                {"threat": "T-23", "test": "test_T23_y::test_x", "outcome": "passed"},
            ]
        )
    )
    passed = cc.passing_tests(res)
    _, gaps, _ = cc.check(THREATS, [meta("T-01"), meta("T-23")], {}, passed)
    assert [g["threat"] for g in gaps] == ["T-01"]


def test_enforcement_date(monkeypatch):
    monkeypatch.setattr(cc, "load_threats", lambda: THREATS)
    monkeypatch.setattr(cc, "load_registry", lambda: [meta("T-23")])
    assert cc.main(["--today", "2026-12-03"]) == 0  # gaps reported, not enforced
    assert cc.main(["--today", "2026-12-04"]) == 1  # freeze: T-01 missing fails


def test_registered_ids_exist_in_the_real_register():
    threats = cc.load_threats()
    assert len(threats) == 37
    assert sum(t["level"] in ("Critical", "High") for t in threats.values()) == 29
    _, _, errors = cc.check(threats, cc.load_registry(), cc.plan_owners())
    assert errors == []


def test_export_parses_register_rows():
    md = (
        "| ID | Threat | STRIDE | Boundary | DFD | OWASP | L × I = risk | Level |\n"
        "| T-04 | Hidden instruction | Tampering | TB-3 | E1 | LLM01 "
        "| 5 × 4 \\= 20 | **Critical** |\n"
        "| T-06 | Blog leak (optional: blog) | Info | TB-5 | E3 | LLM02 "
        "| 5 × 4 \\= 20 | **Critical** |\n"
    )
    rows = et.parse(md)
    assert rows[0][:8] == [
        "T-04",
        "Hidden instruction",
        "Tampering",
        "TB-3",
        "5",
        "4",
        "20",
        "Critical",
    ]
    assert rows[1][8] == "yes"
