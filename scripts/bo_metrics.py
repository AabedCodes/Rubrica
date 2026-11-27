#!/usr/bin/env python3
"""Business-objective measurements BO1-BO5 (A9; M1 §1.2, plan A9).

Computes the measures from a SNAPSHOT of D1's tables (01-interfaces.md §3.1)
exported as JSON: {"assignments": [...], "grading_results": [...],
"proposed_grades": [...], "audit_log": [...], "chat_transcripts": [...],
"manual_queue": [...]}, one object per row with the column names of the schema.

Why a snapshot and not a live query: no runtime database role may read all of
these tables (§3.2; rubrica_owner is for migrations only), so a read-only
reporting role or an export step has to be agreed with D first (A9 worklog).

  BO1  time from an assignment's deadline to its last proposed grade
  BO2  delegated to scripts/bo2_compare.py (A4); this script exports the
       agent's per-criterion scores for it (--export-agent-scores)
  BO3  instructor time to review and approve, vs time to hand-grade
  BO4  chat questions answered without referring to the instructor
  BO5  released grades without a matching approval in the audit log (must be 0)

Only figures this script prints may go in the report or slides (plan A9).

Usage:
  python scripts/bo_metrics.py SNAPSHOT.json [--json]
  python scripts/bo_metrics.py SNAPSHOT.json --export-agent-scores OUT.csv [--essay-map MAP.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

# BO4: the fixed sentence the chat agent uses to refer a student to the
# instructor (to be agreed with C in prompts/chat.md; plan A9). ASSUMED until then.
REFERRAL_SENTENCE = "Please ask your instructor"

# BO3: audit actions that mark the start and end of a human review. ASSUMED
# names; §8 lists "approve_release, decide_appeal, pause, …" and leaves the rest open.
REVIEW_OPEN, REVIEW_DONE = "open_review", "approve_release"
MANUAL_OPEN, MANUAL_DONE = "open_manual_item", "manual_grade"


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _floor_half(n: float) -> float:
    return math.floor(n * 2) / 2


@dataclass
class BO1:
    per_assignment: dict[
        str, float
    ]  # hours from due_at to last result (negative = before the deadline)
    median_hours: float | None


@dataclass
class BO3:
    review_seconds: list[float]
    manual_seconds: list[float]
    median_review: float | None
    median_manual: float | None


@dataclass
class BO4:
    questions: int
    answered_without_referral: int
    share: float | None


@dataclass
class BO5:
    released: int
    without_approval: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.without_approval


def bo1(snapshot: dict) -> BO1:
    """Hours from each assignment's deadline to its last proposed grade."""
    due = {a["id"]: _ts(a["due_at"]) for a in snapshot.get("assignments", [])}
    runs = {r["id"]: r["assignment_id"] for r in snapshot.get("grading_runs", [])}
    last: dict[str, datetime] = {}
    for r in snapshot.get("grading_results", []):
        a = runs.get(r["run_id"])
        if a in due:
            t = _ts(r["created_at"])
            last[a] = max(last.get(a, t), t)
    hours = {a: round((t - due[a]).total_seconds() / 3600, 2) for a, t in last.items()}
    return BO1(hours, statistics.median(hours.values()) if hours else None)


def _durations(rows: list[dict], start: str, end: str, key: str) -> list[float]:
    """Seconds from the first `start` row to the first later `end` row, per record key."""
    opened: dict[str, datetime] = {}
    out: list[float] = []
    for r in sorted(rows, key=lambda r: r["ts"]):
        ids = r.get("args_redacted", {}).get(key)
        ids = ids if isinstance(ids, list) else [ids]
        for rid in ids:
            if rid is None:
                continue
            if r["action"] == start:
                opened.setdefault(rid, _ts(r["ts"]))
            elif r["action"] == end and rid in opened:
                out.append((_ts(r["ts"]) - opened.pop(rid)).total_seconds())
    return out


def bo3(snapshot: dict) -> BO3:
    audit = [
        r
        for r in snapshot.get("audit_log", [])
        if r.get("actor_kind") == "user" and r.get("decision") == "allowed"
    ]
    review = _durations(audit, REVIEW_OPEN, REVIEW_DONE, "proposed_grade_ids")
    manual = _durations(audit, MANUAL_OPEN, MANUAL_DONE, "queue_id")
    return BO3(
        review,
        manual,
        statistics.median(review) if review else None,
        statistics.median(manual) if manual else None,
    )


def bo4(snapshot: dict, referral: str = REFERRAL_SENTENCE) -> BO4:
    """Each student question counts once; answered if the next assistant reply has no referral."""
    questions = answered = 0
    for t in snapshot.get("chat_transcripts", []):
        msgs = t.get("messages", [])
        for i, m in enumerate(msgs):
            if m.get("role") != "user":
                continue
            questions += 1
            reply = next((x for x in msgs[i + 1 :] if x.get("role") == "assistant"), None)
            text = (reply or {}).get("content") or ""
            if text and referral.lower() not in text.lower():
                answered += 1
    return BO4(questions, answered, round(answered / questions, 3) if questions else None)


def bo5(snapshot: dict) -> BO5:
    """Every released grade needs an instructor approval or manual grade in the audit log (R10)."""
    approved: set[str] = set()
    for r in snapshot.get("audit_log", []):
        if r.get("decision") != "allowed" or r.get("actor_kind") != "user":
            continue
        args = r.get("args_redacted", {})
        if r.get("action") == "approve_release":
            approved.update(args.get("proposed_grade_ids", []))
        elif r.get("action") == "manual_grade" and args.get("proposed_grade_id"):
            approved.add(args["proposed_grade_id"])
    released = [
        g["id"] for g in snapshot.get("proposed_grades", []) if g.get("status") == "released"
    ]
    return BO5(len(released), sorted(g for g in released if g not in approved))


def agent_scores(
    snapshot: dict, essay_map: dict[str, str] | None = None
) -> list[dict[str, object]]:
    """Per submission and criterion, the agent's proposed score: the mean of the two
    validated attempts rounded down to 0.5 (§7). Rows for bo2_compare.py (A4)."""
    attempts: dict[tuple[str, str], list[float]] = {}
    for r in snapshot.get("grading_results", []):
        if r.get("validator_status") not in (None, "accepted", "valid"):
            continue
        for crit, score in (r.get("scores") or {}).items():
            attempts.setdefault((r["submission_id"], crit), []).append(float(score))
    rows = []
    for (sub, crit), scores in sorted(attempts.items()):
        essay = (essay_map or {}).get(sub, sub)
        rows.append(
            {
                "essay_id": essay,
                "criterion_id": crit,
                "score": _floor_half(sum(scores) / len(scores)),
            }
        )
    return rows


def compute(snapshot: dict) -> dict:
    five = bo5(snapshot)
    return {
        "BO1": asdict(bo1(snapshot)),
        "BO2": "run scripts/bo2_compare.py on the blind sheet and --export-agent-scores output",
        "BO3": asdict(bo3(snapshot)),
        "BO4": asdict(bo4(snapshot)),
        "BO5": {
            "released": five.released,
            "without_approval": five.without_approval,
            "ok": five.ok,
        },
    }


def render(m: dict) -> str:
    b1, b3, b4, b5 = m["BO1"], m["BO3"], m["BO4"], m["BO5"]

    def fmt(x: float | None, unit: str) -> str:
        return "n/a" if x is None else f"{x:g} {unit}"

    return "\n".join(
        [
            "Rubrica business objectives (synthetic data)",
            f"  BO1 deadline -> last proposed grade: median {fmt(b1['median_hours'], 'h')} "
            f"over {len(b1['per_assignment'])} assignment(s)",
            f"  BO2 {m['BO2']}",
            f"  BO3 review+approve: median {fmt(b3['median_review'], 's')}"
            f" (n={len(b3['review_seconds'])}); "
            f"hand-grade: median {fmt(b3['median_manual'], 's')} (n={len(b3['manual_seconds'])})",
            f"  BO4 answered without referral: {b4['answered_without_referral']}/{b4['questions']}"
            + ("" if b4["share"] is None else f" = {b4['share']:.1%}"),
            f"  BO5 released without approval: {len(b5['without_approval'])} of {b5['released']} "
            + ("(OK)" if b5["ok"] else "(MUST BE ZERO: " + ", ".join(b5["without_approval"]) + ")"),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--export-agent-scores",
        type=Path,
        help="write essay_id,criterion_id,score for bo2_compare.py",
    )
    parser.add_argument(
        "--essay-map", type=Path, help="JSON: submission_id -> essay_id (BO2 sample)"
    )
    args = parser.parse_args(argv)
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))

    if args.export_agent_scores:
        essay_map = (
            json.loads(args.essay_map.read_text(encoding="utf-8")) if args.essay_map else None
        )
        rows = agent_scores(snapshot, essay_map)
        with args.export_agent_scores.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f, fieldnames=["essay_id", "criterion_id", "score"], lineterminator="\n"
            )
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows)} agent criterion scores to {args.export_agent_scores}")
        return 0

    metrics = compute(snapshot)
    print(json.dumps(metrics, indent=2) if args.json else render(metrics))
    return 0 if metrics["BO5"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
