"""Verification test framework (B1, 01-interfaces.md §11).

Every verification test is decorated with @verification(...). The decorator
validates the metadata when the test module is imported, so a wrong threat ID,
control ID, canary or code location fails at collection time, not in the
report three weeks later. The pytest plugin (plugin.py) records each test's
outcome, its `observed` sentence and its evidence; scripts/verify_report.py
turns that into docs/verification/report.md and matrix_rows.csv.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

THREAT_RE = re.compile(r"^T-\d{2}$")
CONTROL_RE = re.compile(r"^C\d{2}$")
CANARY_RE = re.compile(r"CANARY-T(\d{2})-[0-9a-f]{4}")
INPUT_PREFIX = "input:"
KINDS = ("deterministic", "probabilistic")

Kind = Literal["deterministic", "probabilistic"]

# Every decorated test, in import order. The report uses the recorded results,
# not this list; the coverage check (B8) uses this list to find untested threats.
REGISTRY: list[dict[str, Any]] = []


class VerificationMetadataError(ValueError):
    """Raised at import time when a @verification decorator is filled in wrongly."""


def _controls(control: str | list[str] | tuple[str, ...]) -> list[str]:
    items = [control] if isinstance(control, str) else list(control)
    if not items:
        raise VerificationMetadataError("control: name at least one control, e.g. 'C31'")
    for c in items:
        if not CONTROL_RE.match(c):
            raise VerificationMetadataError(f"control {c!r}: use the form C01..C99")
    return items


def _locations(location: str) -> list[str]:
    """`path[:symbol]` items separated by ';'. Each path must exist in the repo."""
    parts = [p.strip() for p in location.split(";") if p.strip()]
    if not parts:
        raise VerificationMetadataError("location: name the file(s) that implement the control")
    for part in parts:
        path = part.split(":", 1)[0]
        if not (REPO_ROOT / path).exists():
            raise VerificationMetadataError(
                f"location {part!r}: {path} does not exist. The matrix must point at real code"
            )
    return parts


def _check_canary(threat: str, canary: str) -> None:
    canary = canary.strip()
    if not canary:
        raise VerificationMetadataError(
            "canary: give the CANARY-T<nn>-<hex> string, or 'input: <what the test feeds in>'"
        )
    found = CANARY_RE.findall(canary)
    if found:
        number = threat.split("-")[1]
        wrong = sorted({n for n in found if n != number})
        if wrong:
            raise VerificationMetadataError(
                f"canary names T-{', T-'.join(wrong)} but the test is for {threat}"
            )
    elif not canary.lower().startswith(INPUT_PREFIX):
        raise VerificationMetadataError(
            "canary: injected text must contain CANARY-T<nn>-<4 hex>; for tests that inject "
            "nothing, start with 'input:' and describe the input"
        )


def verification(
    *,
    threat: str,
    control: str | list[str] | tuple[str, ...],
    location: str,
    canary: str,
    expected: str,
    kind: Kind = "deterministic",
    runs: int = 1,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a test as verification evidence for one threat.

    threat    "T-04"
    control   "C18" or ["C18", "C02"]
    location  "backend/x.py:func; backend/y.py:Class.method" (paths must exist)
    canary    the injected CANARY-T<nn>-<hex> string, or "input: <description>"
    expected  what the control guarantees, in one or two sentences
    kind      "deterministic" (CI, every push) or "probabilistic" (live model, N runs)
    runs      planned runs for probabilistic tests (make verify-live RUNS=N overrides)
    """
    if not THREAT_RE.match(threat):
        raise VerificationMetadataError(f"threat {threat!r}: use the form T-01..T-99")
    controls = _controls(control)
    locations = _locations(location)
    _check_canary(threat, canary)
    if not expected.strip():
        raise VerificationMetadataError("expected: say what the control guarantees")
    if kind not in KINDS:
        raise VerificationMetadataError(f"kind {kind!r}: use one of {KINDS}")
    if runs < 1 or (kind == "deterministic" and runs != 1):
        raise VerificationMetadataError("runs: 1 for deterministic tests, >= 1 for probabilistic")

    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        meta = {
            "threat": threat,
            "control": controls,
            "location": locations,
            "canary": canary.strip(),
            "expected": expected.strip(),
            "kind": kind,
            "runs": runs,
            "test": f"{fn.__module__}::{fn.__name__}",
        }
        REGISTRY.append(meta)
        fn = pytest.mark.verification(meta=meta)(fn)
        return getattr(pytest.mark, kind)(fn)

    return deco
