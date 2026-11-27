#!/usr/bin/env python3
"""Turn verification results into the evidence report (B1, 01-interfaces.md §11).

Usage: python scripts/verify_report.py RESULTS.json [MORE.json ...] [--out DIR]

Reads one or more results files written by pytest --verification-results
(several files = repeated live runs) and writes, in DIR (default
docs/verification):
  report.md        one row per test: threat, controls, canary, expected,
                   observed, result (pass/fail/skip, or k/N for repeated runs),
                   provider and models for live runs, date
  report.json      the same rows, machine-readable
  matrix_rows.csv  threat, control, location, test, result: one row per
                   control per location, for the traceability matrix (B9)

Exit code 0 when every test that ran passed, 1 otherwise. Skips don't fail
the run; they are listed as skipped, with their reason, so gaps stay visible.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path


def load(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        records.extend(json.loads(path.read_text(encoding="utf-8")))
    return records


def aggregate(records: list[dict]) -> list[dict]:
    """One row per test. Repeated runs of the same test become k/N."""
    by_test: OrderedDict[str, list[dict]] = OrderedDict()
    for rec in sorted(records, key=lambda r: (r["threat"], r["nodeid"], r.get("run", 1))):
        by_test.setdefault(rec["nodeid"], []).append(rec)

    rows = []
    for nodeid, recs in by_test.items():
        last = recs[-1]
        ran = [r for r in recs if r["outcome"] != "skipped"]
        passed = sum(r["outcome"] == "passed" for r in ran)
        if not ran:
            result, status = "skipped", "skipped"
        elif last["kind"] == "probabilistic" or len(ran) > 1:
            result = f"{passed}/{len(ran)}"
            status = "passed" if passed == len(ran) else "partial" if passed else "failed"
        else:
            result = status = last["outcome"]
        observed = last.get("observed") or (
            last.get("reason") if not ran or status != "passed" else ""
        )
        rows.append(
            {
                "test": nodeid,
                "threat": last["threat"],
                "control": last["control"],
                "location": last["location"],
                "canary": last["canary"],
                "expected": last["expected"],
                "observed": observed or "",
                "kind": last["kind"],
                "result": result,
                "status": status,
                "provider": last.get("provider", ""),
                "models": last.get("models", {}),
                "evidence": last.get("evidence", []),
                "date": last.get("finished_at", "")[:10],
            }
        )
    return rows


def _cell(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def render_markdown(rows: list[dict]) -> str:
    counts = {
        s: sum(r["status"] == s for r in rows) for s in ("passed", "partial", "failed", "skipped")
    }
    threats = sorted({r["threat"] for r in rows})
    lines = [
        "# Verification evidence report",
        "",
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by "
        "`scripts/verify_report.py` from the verification test run. Do not edit by hand.",
        "",
        f"**{len(rows)} tests** covering **{len(threats)} threats**: "
        f"{counts['passed']} passed, {counts['partial']} partial (probabilistic), "
        f"{counts['failed']} failed, {counts['skipped']} skipped.",
        "",
        "| Test | Threat | Controls | Canary / input | Expected | Observed | Result | Model "
        "| Date |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        model = ""
        if r["provider"] not in ("", "fake"):
            model = r["provider"] + (
                ": " + ", ".join(f"{k}={v}" for k, v in r["models"].items()) if r["models"] else ""
            )
        lines.append(
            "| "
            + " | ".join(
                _cell(x)
                for x in (
                    f"`{r['test'].split('::')[-1]}`",
                    r["threat"],
                    ", ".join(r["control"]),
                    r["canary"],
                    r["expected"],
                    r["observed"],
                    f"**{r['result']}**",
                    model or "fake / n/a",
                    r["date"],
                )
            )
            + " |"
        )
    lines += ["", "Full test IDs and evidence are in `report.json`.", ""]
    return "\n".join(lines)


def write_matrix(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["threat", "control", "location", "test", "result"])
        for r in rows:
            for control in r["control"]:
                for location in r["location"]:
                    w.writerow([r["threat"], control, location, r["test"], r["result"]])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("results", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, default=Path("docs/verification"))
    args = ap.parse_args(argv)

    rows = aggregate(load(args.results))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.md").write_text(render_markdown(rows), encoding="utf-8")
    (args.out / "report.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    write_matrix(rows, args.out / "matrix_rows.csv")

    bad = [r for r in rows if r["status"] in ("failed", "partial")]
    print(f"verify_report: {len(rows)} tests, {len(bad)} not fully passing -> {args.out}/report.md")
    for r in bad:
        print(f"  {r['status'].upper():8} {r['threat']} {r['test']}  {r['observed']}")
    return 1 if any(r["status"] == "failed" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
