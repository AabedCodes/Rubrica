#!/usr/bin/env python3
"""Export the M1 threat register (report Section 5 table) to docs/threat-model/threats.csv (B8).

Usage: python scripts/export_threats.py "<path to M1 report .md>"

Reads every table row whose first cell is a threat ID (T-nn) and writes:
id, threat, stride, boundary, likelihood, impact, risk, level, optional_feature.
Rerun it if the register is re-rated; the coverage check reads the CSV.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROW = re.compile(r"^\|\s*(T-\d{2})\s*\|")
SCORE = re.compile(r"(\d)\s*[×xX]\s*(\d)\s*\\?=\s*(\d+)")
OUT = Path(__file__).resolve().parent.parent / "docs" / "threat-model" / "threats.csv"
HEADER = [
    "id",
    "threat",
    "stride",
    "boundary",
    "likelihood",
    "impact",
    "risk",
    "level",
    "optional_feature",
]


def parse(markdown: str) -> list[list[str]]:
    rows: dict[str, list[str]] = {}
    for line in markdown.splitlines():
        if not ROW.match(line):
            continue
        cells = [c.strip().replace("\\", "") for c in line.strip().strip("|").split("|")]
        if len(cells) < 8:
            continue
        tid, title, stride, boundary = cells[0], cells[1], cells[2], cells[3]
        score, level = cells[-2], cells[-1].strip("*").strip()
        m = SCORE.search(score.replace("\\", ""))
        if not m or tid in rows:  # first occurrence is the Section 5 register
            continue
        lik, imp, risk = m.groups()
        optional = "yes" if "(optional" in title.lower() else "no"
        rows[tid] = [tid, title, stride, boundary, lik, imp, risk, level, optional]
    return [rows[k] for k in sorted(rows)]


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    rows = parse(Path(argv[0]).read_text(encoding="utf-8"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(rows)
    levels: dict[str, int] = {}
    for r in rows:
        levels[r[7]] = levels.get(r[7], 0) + 1
    print(f"wrote {len(rows)} threats to {OUT}: {levels}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
