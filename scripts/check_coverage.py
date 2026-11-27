#!/usr/bin/env python3
"""Verification coverage check (B8).

Usage: python scripts/check_coverage.py [--results build/verification/results.json]
                                        [--enforce-from 2026-12-04] [--out PATH]

Fails (exit 1) when:
  - a Critical or High threat in docs/threat-model/threats.csv has no
    @verification test (with --results: no *passing* test);
  - a test names a threat that isn't in the register, or a control outside
    C01..C37 (C01-C30 from M1, C31-C37 added in the M2 plan).

Before --enforce-from (default: Fri 4 Dec 2026, the feature freeze), gaps are
reported but the exit code is 0, so CI shows the list without blocking work.
Metadata errors (unknown threat/control) always fail.

The owner of each missing test is read from the "Verification tests" lists in
docs/plan/<letter>-*.md, so the output says who to chase.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THREATS = ROOT / "docs" / "threat-model" / "threats.csv"
TEST_DIR = ROOT / "tests" / "verification"
PLAN_DIR = ROOT / "docs" / "plan"
VALID_CONTROLS = {f"C{i:02d}" for i in range(1, 38)}
REQUIRED_LEVELS = {"Critical", "High"}
FREEZE = date(2026, 12, 4)

# Who holds each role now (docs/worklog, 28 Nov: E also covers B).
ROLE_NAMES = {"A": "Joudy", "B": "Aabed (B)", "C": "Nour", "D": "Maha", "E": "Aabed"}


def load_threats(path: Path = THREATS) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        return {row["id"]: row for row in csv.DictReader(f)}


def load_registry() -> list[dict]:
    """Import every tests/verification/test_*.py; the decorator fills REGISTRY."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    framework = importlib.import_module("tests.verification.framework")
    framework.REGISTRY.clear()
    for path in sorted(TEST_DIR.glob("test_*.py")):
        importlib.import_module(f"tests.verification.{path.stem}")
    return list(framework.REGISTRY)


def plan_owners(plan_dir: Path = PLAN_DIR) -> dict[str, list[str]]:
    """T-nn -> role letters whose plan file lists a test_T<nn>_... file."""
    owners: dict[str, list[str]] = {}
    for path in sorted(plan_dir.glob("[A-E]-*.md")):
        letter = path.name[0]
        for n in sorted(set(re.findall(r"test_T(\d{2})_", path.read_text(encoding="utf-8")))):
            owners.setdefault(f"T-{n}", [])
            if letter not in owners[f"T-{n}"]:
                owners[f"T-{n}"].append(letter)
    return owners


def _key(threat: str, test_id: str) -> str:
    # pytest imports test modules by basename, this script by package path, so
    # match on threat + function name (unique within a threat's file).
    return f"{threat}::{test_id.split('::')[-1]}"


def passing_tests(results_path: Path) -> dict[str, bool]:
    """threat::function -> passed at least once in the results file."""
    out: dict[str, bool] = {}
    for rec in json.loads(results_path.read_text(encoding="utf-8")):
        key = _key(rec["threat"], rec["test"])
        out[key] = out.get(key, False) or rec["outcome"] == "passed"
    return out


def check(threats, registry, owners, passed=None):
    errors: list[str] = []
    for meta in registry:
        if meta["threat"] not in threats:
            errors.append(f"{meta['test']}: threat {meta['threat']} is not in threats.csv")
        for c in meta["control"]:
            if c not in VALID_CONTROLS:
                errors.append(f"{meta['test']}: control {c} doesn't exist (C01..C37)")

    rows = []
    for tid, t in threats.items():
        tests = [m for m in registry if m["threat"] == tid]
        ok = [m for m in tests if passed is None or passed.get(_key(tid, m["test"]), False)]
        rows.append(
            {
                "threat": tid,
                "level": t["level"],
                "title": t["threat"],
                "tests": len(tests),
                "covered": bool(ok),
                "required": t["level"] in REQUIRED_LEVELS,
                "owners": owners.get(tid, []),
            }
        )
    gaps = [r for r in rows if r["required"] and not r["covered"]]
    return rows, gaps, errors


def render(rows, gaps, errors, mode: str) -> str:
    req = [r for r in rows if r["required"]]
    lines = [
        "# Verification coverage (B8)",
        "",
        f"{len(req) - len(gaps)} of {len(req)} Critical and High threats have a {mode} test.",
        "",
        "| Threat | Level | Tests | Covered | Owner(s) per plan |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        who = ", ".join(f"{o} ({ROLE_NAMES.get(o, '?')})" for o in r["owners"]) or "unassigned"
        mark = "yes" if r["covered"] else ("**no**" if r["required"] else "no")
        lines.append(f"| {r['threat']} | {r['level']} | {r['tests']} | {mark} | {who} |")
    if errors:
        lines += ["", "## Metadata errors", *[f"- {e}" for e in errors]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", type=Path, help="results.json: require a passing test")
    ap.add_argument("--enforce-from", type=date.fromisoformat, default=FREEZE)
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    ap.add_argument("--out", type=Path, help="also write the table as Markdown here")
    args = ap.parse_args(argv)

    threats = load_threats()
    registry = load_registry()
    passed = passing_tests(args.results) if args.results else None
    rows, gaps, errors = check(threats, registry, plan_owners(), passed)
    mode = "passing" if passed is not None else "registered"
    report = render(rows, gaps, errors, mode)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")

    enforcing = args.today >= args.enforce_from
    state = "enforced" if enforcing else f"report only until {args.enforce_from}"
    print(
        f"check_coverage: {len(registry)} verification tests, {len(gaps)} required threats "
        f"without a {mode} test ({state})"
    )
    for g in gaps:
        who = ", ".join(f"{o} ({ROLE_NAMES.get(o, '?')})" for o in g["owners"]) or "unassigned"
        print(f"  MISSING {g['threat']} [{g['level']}] {g['title']}  -> {who}")
    for e in errors:
        print(f"  ERROR   {e}")
    if errors or (gaps and enforcing):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
