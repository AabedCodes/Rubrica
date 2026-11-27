#!/usr/bin/env python3
"""Compare blind hand grades with the agent's scores (A4/A9; BO2, T-37).

Run only after the blind sheet is complete. Inputs:

  seed/blind_grades.csv      filled in by a teammate who is not C, without
                             seeing agent scores (from bo2_blind_sheet.py)
  seed/bo2/sample_map.json   sample ID -> essay ID
  an agent-scores CSV        columns essay_id, criterion_id, score: the agent's
                             proposed score per criterion, exported from
                             grading_results after a run on the real model

Reports, for the final report and slides (only figures this script prints):
  - n: criterion scores compared, and how many essays
  - BO2: share of agent criterion scores within one rubric point of the blind score
  - the same share per criterion, and the mean absolute difference
  - "confidently wrong" cases: the agent is CONFIDENT_GAP or more points away

Usage: python scripts/bo2_compare.py AGENT_SCORES.csv [--blind PATH] [--map PATH] [--json]
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WITHIN = 1.0  # BO2: "within one rubric point" (M1 §1.2)
CONFIDENT_GAP = 2.0  # starting threshold for "confidently wrong"; record the final one


class SheetError(ValueError):
    """The inputs are incomplete or inconsistent; no figures are produced."""


@dataclass(frozen=True)
class Pair:
    essay_id: str
    criterion_id: str
    max_points: float
    blind: float
    agent: float

    @property
    def gap(self) -> float:
        return abs(self.agent - self.blind)


@dataclass(frozen=True)
class Report:
    n_scores: int
    n_essays: int
    within_one: int
    within_one_share: float
    mean_abs_difference: float
    per_criterion: dict[str, dict[str, float]]
    confidently_wrong: list[dict[str, object]]


def _score(value: str, max_points: float, where: str) -> float:
    try:
        n = float(value)
    except ValueError as e:
        raise SheetError(f"{where}: score {value!r} is not a number") from e
    if not 0 <= n <= max_points or (n * 2) % 1 != 0:
        raise SheetError(f"{where}: score {n:g} must be 0..{max_points:g} in steps of 0.5")
    return n


def read_blind(
    path: Path, sample_map: dict[str, str]
) -> dict[tuple[str, str], tuple[float, float]]:
    """(essay_id, criterion_id) -> (blind score, max points). Every row must be filled."""
    out: dict[tuple[str, str], tuple[float, float]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            where = f"{path.name} line {i}"
            if row["sample_id"] not in sample_map:
                raise SheetError(f"{where}: unknown sample {row['sample_id']}")
            if not row["score"].strip():
                raise SheetError(f"{where}: no blind score yet; finish the sheet first")
            max_points = float(row["max_points"])
            key = (sample_map[row["sample_id"]], row["criterion_id"])
            out[key] = (_score(row["score"].strip(), max_points, where), max_points)
    if not out:
        raise SheetError(f"{path.name} has no rows")
    return out


def read_agent(path: Path) -> dict[tuple[str, str], str]:
    with path.open(newline="", encoding="utf-8") as f:
        return {(r["essay_id"], r["criterion_id"]): r["score"].strip() for r in csv.DictReader(f)}


def pair_up(
    blind: dict[tuple[str, str], tuple[float, float]], agent: dict[tuple[str, str], str]
) -> list[Pair]:
    missing = sorted(set(blind) - set(agent))
    if missing:
        raise SheetError(
            f"agent scores missing for {len(missing)} criterion scores, e.g. {missing[0]}"
        )
    return [
        Pair(e, c, mx, b, _score(agent[(e, c)], mx, f"agent {e}/{c}"))
        for (e, c), (b, mx) in sorted(blind.items())
    ]


def compare(pairs: list[Pair]) -> Report:
    within = [p for p in pairs if p.gap <= WITHIN]
    per: dict[str, dict[str, float]] = {}
    for crit in sorted({p.criterion_id for p in pairs}):
        ps = [p for p in pairs if p.criterion_id == crit]
        ok = sum(p.gap <= WITHIN for p in ps)
        per[crit] = {"n": len(ps), "within_one": ok, "within_one_share": round(ok / len(ps), 3)}
    wrong = [
        {
            "essay_id": p.essay_id,
            "criterion_id": p.criterion_id,
            "blind": p.blind,
            "agent": p.agent,
            "gap": p.gap,
        }
        for p in sorted(pairs, key=lambda p: (-p.gap, p.essay_id, p.criterion_id))
        if p.gap >= CONFIDENT_GAP
    ]
    return Report(
        n_scores=len(pairs),
        n_essays=len({p.essay_id for p in pairs}),
        within_one=len(within),
        within_one_share=round(len(within) / len(pairs), 3),
        mean_abs_difference=round(sum(p.gap for p in pairs) / len(pairs), 3),
        per_criterion=per,
        confidently_wrong=wrong,
    )


def render(report: Report) -> str:
    lines = [
        "BO2 blind-sample comparison (synthetic essays, graded by a student acting as instructor)",
        f"  essays: {report.n_essays}   criterion scores: {report.n_scores}",
        f"  within {WITHIN:g} point: {report.within_one}/{report.n_scores}"
        f" = {report.within_one_share:.1%}",
        f"  mean absolute difference: {report.mean_abs_difference:g} points",
    ]
    for crit, s in report.per_criterion.items():
        lines.append(
            f"  {crit}: {s['within_one']:g}/{s['n']:g} within {WITHIN:g}"
            f" ({s['within_one_share']:.1%})"
        )
    lines.append(f"  confidently wrong (gap >= {CONFIDENT_GAP:g}): {len(report.confidently_wrong)}")
    lines += [
        f"    {w['essay_id']} {w['criterion_id']}: blind {w['blind']:g}, agent {w['agent']:g}"
        for w in report.confidently_wrong
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("agent_scores", type=Path)
    parser.add_argument("--blind", type=Path, default=ROOT / "seed" / "blind_grades.csv")
    parser.add_argument("--map", type=Path, default=ROOT / "seed" / "bo2" / "sample_map.json")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)
    try:
        sample_map = json.loads(args.map.read_text(encoding="utf-8"))
        report = compare(pair_up(read_blind(args.blind, sample_map), read_agent(args.agent_scores)))
    except SheetError as e:
        print(f"bo2_compare: {e}")
        return 2
    print(json.dumps(asdict(report), indent=2) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
