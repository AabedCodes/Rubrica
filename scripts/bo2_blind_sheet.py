#!/usr/bin/env python3
"""Build the BO2 blind hand-grading sample (A4; BO2, T-37).

Reads the synthetic essays (seed/bo2/essays.json) and writes, for a teammate
who is not C to grade by hand BEFORE seeing any agent score:

  seed/bo2/blind_packet.md   the essays in a shuffled order under opaque
                             sample IDs, with the rubric (labels and maxima)
  seed/blind_grades.csv      one row per sample and criterion, score empty
  seed/bo2/sample_map.json   sample ID -> essay ID, used only by bo2_compare.py

By construction this script reads nothing but the essays file: it has no
access to agent scores, so the sheet can't show them (plan A4/A9).

Usage: python scripts/bo2_blind_sheet.py [--essays PATH] [--out-dir DIR] [--salt TEXT]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ESSAYS = ROOT / "seed" / "bo2" / "essays.json"
SHEET_COLUMNS = [
    "sample_id",
    "criterion_id",
    "criterion_label",
    "max_points",
    "score",
    "grader",
    "notes",
]


@dataclass(frozen=True)
class Criterion:
    criterion_id: str
    label: str
    max_points: float


@dataclass(frozen=True)
class Sample:
    sample_id: str
    essay_id: str
    text: str


def load_essays(path: Path) -> tuple[dict, list[Criterion], list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assignment = data["assignment"]
    criteria = [
        Criterion(c["criterion_id"], c["label"], float(c["max_points"]))
        for c in assignment["criteria"]
    ]
    essays = data["essays"]
    ids = [e["essay_id"] for e in essays]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate essay_id in essays file")
    return assignment, criteria, essays


def opaque_id(salt: str, essay_id: str) -> str:
    """A sample ID that doesn't reveal the essay or its position in the file."""
    return "S-" + hashlib.sha256(f"{salt}:{essay_id}".encode()).hexdigest()[:6].upper()


def build_samples(essays: list[dict], salt: str) -> list[Sample]:
    samples = [Sample(opaque_id(salt, e["essay_id"]), e["essay_id"], e["text"]) for e in essays]
    if len({s.sample_id for s in samples}) != len(samples):
        raise ValueError("sample ID collision: choose another salt")
    # Deterministic shuffle: order by the opaque ID, not by the file's order.
    return sorted(samples, key=lambda s: s.sample_id)


def render_packet(assignment: dict, criteria: list[Criterion], samples: list[Sample]) -> str:
    lines = [
        f"# Blind grading packet: {assignment['title']}",
        "",
        "Synthetic essays written by the team (A4). Grade each one against the rubric",
        "below and enter your scores in `seed/blind_grades.csv`. **Do not look at any",
        "agent score, review screen or grading result before you have finished.**",
        "",
        "Scores: from 0 to each criterion's maximum, in steps of 0.5.",
        "",
        "## Task given to the students",
        "",
        assignment["instructions"],
        "",
        "## Rubric",
        "",
        "| Criterion ID | Criterion | Max |",
        "|---|---|---|",
        *[f"| `{c.criterion_id}` | {c.label} | {c.max_points:g} |" for c in criteria],
        "",
    ]
    for s in samples:
        lines += [f"## {s.sample_id}", "", s.text, ""]
    return "\n".join(lines)


def write_sheet(path: Path, criteria: list[Criterion], samples: list[Sample]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")  # repo stores LF
        writer.writerow(SHEET_COLUMNS)
        for s in samples:
            for c in criteria:
                writer.writerow(
                    [s.sample_id, c.criterion_id, c.label, f"{c.max_points:g}", "", "", ""]
                )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--essays", type=Path, default=DEFAULT_ESSAYS)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "seed")
    parser.add_argument("--salt", default="rubrica-bo2-v1", help="changes the sample IDs and order")
    parser.add_argument("--force", action="store_true", help="overwrite an existing grades sheet")
    args = parser.parse_args(argv)

    assignment, criteria, essays = load_essays(args.essays)
    samples = build_samples(essays, args.salt)
    sheet = args.out_dir / "blind_grades.csv"
    if sheet.exists() and not args.force:
        print(f"{sheet} exists (it may already hold blind scores); use --force to overwrite")
        return 1
    (args.out_dir / "bo2").mkdir(parents=True, exist_ok=True)
    (args.out_dir / "bo2" / "blind_packet.md").write_text(
        render_packet(assignment, criteria, samples), encoding="utf-8"
    )
    write_sheet(sheet, criteria, samples)
    sample_map = {s.sample_id: s.essay_id for s in samples}
    (args.out_dir / "bo2" / "sample_map.json").write_text(
        json.dumps(sample_map, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(samples)} samples x {len(criteria)} criteria to {sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
