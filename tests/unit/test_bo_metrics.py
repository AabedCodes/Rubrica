"""BO1-BO5 measurements (A9) on a synthetic snapshot of D1's tables."""

import csv
import json
from pathlib import Path

import bo_metrics as bo
import pytest

A1, A2 = "assign-1", "assign-2"
RUN1, RUN2 = "run-1", "run-2"


def snapshot() -> dict:
    return {
        "assignments": [
            {"id": A1, "due_at": "2026-12-01T12:00:00+00:00"},
            {"id": A2, "due_at": "2026-12-02T12:00:00+00:00"},
        ],
        "grading_runs": [{"id": RUN1, "assignment_id": A1}, {"id": RUN2, "assignment_id": A2}],
        "grading_results": [
            # A1: last result 3 hours after the deadline
            {
                "run_id": RUN1,
                "submission_id": "s1",
                "attempt": 1,
                "scores": {"c1": 3, "c2": 4},
                "created_at": "2026-12-01T13:00:00+00:00",
                "validator_status": "accepted",
            },
            {
                "run_id": RUN1,
                "submission_id": "s1",
                "attempt": 2,
                "scores": {"c1": 4, "c2": 4},
                "created_at": "2026-12-01T15:00:00+00:00",
                "validator_status": "accepted",
            },
            # rejected attempt: ignored for agent scores
            {
                "run_id": RUN1,
                "submission_id": "s2",
                "attempt": 1,
                "scores": {"c1": 99},
                "created_at": "2026-12-01T14:00:00+00:00",
                "validator_status": "rejected",
            },
            # A2: last result 1 hour after the deadline
            {
                "run_id": RUN2,
                "submission_id": "s3",
                "attempt": 1,
                "scores": {"c1": 2},
                "created_at": "2026-12-02T13:00:00+00:00",
                "validator_status": "accepted",
            },
        ],
        "proposed_grades": [
            {"id": "g1", "status": "released"},
            {"id": "g2", "status": "released"},
            {"id": "g3", "status": "pending"},
            {"id": "g4", "status": "released"},
        ],
        "audit_log": [
            {
                "ts": "2026-12-01T16:00:00+00:00",
                "actor_kind": "user",
                "decision": "allowed",
                "action": "open_review",
                "args_redacted": {"proposed_grade_ids": ["g1"]},
            },
            {
                "ts": "2026-12-01T16:02:00+00:00",
                "actor_kind": "user",
                "decision": "allowed",
                "action": "approve_release",
                "args_redacted": {"proposed_grade_ids": ["g1"]},
            },
            {
                "ts": "2026-12-01T16:10:00+00:00",
                "actor_kind": "user",
                "decision": "allowed",
                "action": "open_review",
                "args_redacted": {"proposed_grade_ids": ["g2"]},
            },
            {
                "ts": "2026-12-01T16:14:00+00:00",
                "actor_kind": "user",
                "decision": "allowed",
                "action": "approve_release",
                "args_redacted": {"proposed_grade_ids": ["g2"]},
            },
            {
                "ts": "2026-12-01T17:00:00+00:00",
                "actor_kind": "user",
                "decision": "allowed",
                "action": "open_manual_item",
                "args_redacted": {"queue_id": "q1"},
            },
            {
                "ts": "2026-12-01T17:15:00+00:00",
                "actor_kind": "user",
                "decision": "allowed",
                "action": "manual_grade",
                "args_redacted": {"queue_id": "q1"},
            },
            # an AGENT row naming g4 must not count as an approval
            {
                "ts": "2026-12-01T18:00:00+00:00",
                "actor_kind": "agent",
                "decision": "allowed",
                "action": "approve_release",
                "args_redacted": {"proposed_grade_ids": ["g4"]},
            },
        ],
        "chat_transcripts": [
            {
                "messages": [
                    {"role": "user", "content": "What is a trust boundary?"},
                    {"role": "assistant", "content": "It is where trust changes."},
                    {"role": "user", "content": "Can I get an extension?"},
                    {
                        "role": "assistant",
                        "content": "Please ask your instructor about extensions.",
                    },
                    {"role": "user", "content": "Thanks"},
                ]
            },
        ],
    }


def test_bo1_hours_from_deadline_to_last_result() -> None:
    r = bo.bo1(snapshot())
    assert r.per_assignment == {A1: 3.0, A2: 1.0}
    assert r.median_hours == 2.0


def test_bo3_review_and_hand_grading_times() -> None:
    r = bo.bo3(snapshot())
    assert sorted(r.review_seconds) == [120.0, 240.0]
    assert r.median_review == 180.0
    assert r.manual_seconds == [900.0]


def test_bo4_counts_referrals_and_unanswered_questions() -> None:
    r = bo.bo4(snapshot())
    # 3 questions: one answered, one referred, one with no reply at all.
    assert (r.questions, r.answered_without_referral, r.share) == (
        3,
        1,
        pytest.approx(0.333, abs=1e-3),
    )


def test_bo5_flags_released_grades_without_a_human_approval() -> None:
    r = bo.bo5(snapshot())
    assert r.released == 3
    assert r.without_approval == ["g4"]  # only an agent row mentions it: that is not an approval
    assert not r.ok


def test_bo5_is_ok_when_every_release_was_approved() -> None:
    s = snapshot()
    s["proposed_grades"] = [g for g in s["proposed_grades"] if g["id"] != "g4"]
    assert bo.bo5(s).ok


def test_agent_scores_follow_the_section_7_rule_and_skip_rejected_attempts() -> None:
    rows = bo.agent_scores(snapshot(), {"s1": "E01"})
    by_key = {(r["essay_id"], r["criterion_id"]): r["score"] for r in rows}
    assert by_key[("E01", "c1")] == 3.5  # mean(3, 4) rounded down to 0.5
    assert by_key[("E01", "c2")] == 4.0
    assert ("s2", "c1") not in by_key  # rejected attempt ignored
    assert by_key[("s3", "c1")] == 2.0  # unmapped submissions keep their ID


def test_cli_prints_figures_and_fails_when_bo5_is_not_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(snapshot()), encoding="utf-8")
    assert bo.main([str(snap)]) == 1
    out = capsys.readouterr().out
    assert "BO1 deadline -> last proposed grade: median 2 h over 2 assignment(s)" in out
    assert "BO5 released without approval: 1 of 3 (MUST BE ZERO: g4)" in out


def test_cli_exports_agent_scores_for_bo2_compare(tmp_path: Path) -> None:
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps(snapshot()), encoding="utf-8")
    mapping = tmp_path / "map.json"
    mapping.write_text(json.dumps({"s1": "E01"}), encoding="utf-8")
    out = tmp_path / "agent.csv"
    assert bo.main([str(snap), "--export-agent-scores", str(out), "--essay-map", str(mapping)]) == 0
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0] == {"essay_id": "E01", "criterion_id": "c1", "score": "3.5"}
