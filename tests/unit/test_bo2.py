"""BO2 blind sample (A4): the sheet never shows agent scores, and the comparison is correct."""

import csv
import json
from pathlib import Path

import bo2_blind_sheet as sheet
import bo2_compare as cmp
import pytest

ESSAYS = Path(__file__).resolve().parents[2] / "seed" / "bo2" / "essays.json"


@pytest.fixture
def built(tmp_path: Path) -> Path:
    assert sheet.main(["--essays", str(ESSAYS), "--out-dir", str(tmp_path)]) == 0
    return tmp_path


def test_seed_essays_are_synthetic_and_varied() -> None:
    data = json.loads(ESSAYS.read_text(encoding="utf-8"))
    essays = data["essays"]
    assert len(essays) >= 10
    assert len({e["essay_id"] for e in essays}) == len(essays)
    lengths = sorted(len(e["text"].split()) for e in essays)
    assert lengths[-1] > 3 * lengths[0]  # weak, short answers next to full ones
    # No hint of the intended quality anywhere in the file.
    for e in essays:
        assert set(e) == {"essay_id", "text"}


def test_sheet_has_one_empty_row_per_sample_and_criterion(built: Path) -> None:
    rows = list(csv.DictReader((built / "blind_grades.csv").open(encoding="utf-8")))
    assert list(rows[0]) == sheet.SHEET_COLUMNS
    assert len(rows) == 12 * 2
    assert all(r["score"] == "" and r["grader"] == "" for r in rows)


def test_sheet_and_packet_never_show_agent_scores_or_essay_ids(built: Path) -> None:
    csv_text = (built / "blind_grades.csv").read_text(encoding="utf-8").lower()
    packet = (built / "bo2" / "blind_packet.md").read_text(encoding="utf-8")
    for forbidden in ("agent", "proposed", "attempt", "model", "e01", "e12"):
        assert forbidden not in csv_text
    assert "E01" not in packet and "E12" not in packet
    # The essays may mention agents and scores (that's their topic), so check everything
    # the script added around them: it must carry no grading result of any kind.
    frame = packet
    for essay in json.loads(ESSAYS.read_text(encoding="utf-8"))["essays"]:
        assert essay["text"] in frame
        frame = frame.replace(essay["text"], "")
    for forbidden in ("proposed", "attempt", "grading_result", "validator", "flag", "/ 5"):
        assert forbidden not in frame.lower()
    assert "Do not look at any\nagent score" in frame


def test_order_is_shuffled_and_ids_opaque(built: Path) -> None:
    mapping = json.loads((built / "bo2" / "sample_map.json").read_text(encoding="utf-8"))
    order = list(mapping.values())
    assert sorted(order) != order or len(order) < 3  # not the file's order
    assert all(k.startswith("S-") and len(k) == 8 for k in mapping)


def test_refuses_to_overwrite_a_sheet_that_may_hold_scores(built: Path) -> None:
    assert sheet.main(["--essays", str(ESSAYS), "--out-dir", str(built)]) == 1


def _fill(built: Path, blind: dict[str, float]) -> Path:
    mapping = json.loads((built / "bo2" / "sample_map.json").read_text(encoding="utf-8"))
    path = built / "blind_grades.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for r in rows:
        r["score"] = str(blind[mapping[r["sample_id"]]])
        r["grader"] = "B"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sheet.SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def _agent_csv(tmp: Path, scores: dict[str, float]) -> Path:
    path = tmp / "agent.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["essay_id", "criterion_id", "score"])
        for essay, s in scores.items():
            for crit in ("bo2-boundary", "bo2-control"):
                w.writerow([essay, crit, s])
    return path


def test_compare_computes_bo2_and_confidently_wrong(
    built: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    essays = [f"E{i:02d}" for i in range(1, 13)]
    blind = dict.fromkeys(essays, 3.0)
    agent = dict.fromkeys(essays, 3.5)
    agent["E01"] = 5.0  # 2 points off on both criteria: confidently wrong
    agent["E02"] = 4.5  # 1.5 off: outside one point, not "confidently"
    _fill(built, blind)
    code = cmp.main(
        [
            str(_agent_csv(built, agent)),
            "--blind",
            str(built / "blind_grades.csv"),
            "--map",
            str(built / "bo2" / "sample_map.json"),
            "--json",
        ]
    )
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["n_scores"] == 24 and report["n_essays"] == 12
    assert report["within_one"] == 20  # 10 essays x 2 criteria
    assert report["within_one_share"] == pytest.approx(20 / 24, abs=1e-3)
    assert {(w["essay_id"], w["gap"]) for w in report["confidently_wrong"]} == {("E01", 2.0)}
    assert report["per_criterion"]["bo2-control"]["within_one"] == 10


def test_compare_refuses_an_unfinished_sheet(
    built: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agent = _agent_csv(built, {f"E{i:02d}": 3.0 for i in range(1, 13)})
    code = cmp.main(
        [
            str(agent),
            "--blind",
            str(built / "blind_grades.csv"),
            "--map",
            str(built / "bo2" / "sample_map.json"),
        ]
    )
    assert code == 2
    assert "finish the sheet first" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["6", "-1", "2.3", "x"])
def test_compare_rejects_out_of_range_scores(built: Path, bad: str) -> None:
    mapping = json.loads((built / "bo2" / "sample_map.json").read_text(encoding="utf-8"))
    with pytest.raises(cmp.SheetError):
        cmp._score(bad, 5.0, "test")
    assert mapping  # sheet built


def test_compare_requires_every_agent_score(built: Path) -> None:
    essays = {f"E{i:02d}": 3.0 for i in range(1, 13)}
    _fill(built, essays)
    mapping = json.loads((built / "bo2" / "sample_map.json").read_text(encoding="utf-8"))
    blind = cmp.read_blind(built / "blind_grades.csv", mapping)
    agent = {k: "3" for k in list(blind)[:-1]}
    with pytest.raises(cmp.SheetError, match="agent scores missing"):
        cmp.pair_up(blind, agent)
