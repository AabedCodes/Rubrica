"""Pytest hooks and shared fixtures for verification tests (B1).

Loaded by tests/conftest.py. Records, for every test marked by
@verification: outcome, the `observed` sentence the test set, the evidence it
attached, the provider/model for live runs, and the time. With
`--verification-results=PATH` the records are written to PATH as JSON, which
scripts/verify_report.py turns into the report and matrix rows.

Fixtures for components that don't exist yet skip with a message naming the
task that provides them. Tests written against them today start running the
day that code lands, with no change to the test.
"""

from __future__ import annotations

import importlib
import json
import os
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

RESULTS_KEY = pytest.StashKey[list[dict[str, Any]]]()
LIVE_PROVIDERS_EXCLUDED = {"", "fake"}


# ---------------------------------------------------------------- options and hooks


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("rubrica verification")
    group.addoption(
        "--verification-results",
        metavar="PATH",
        default=None,
        help="write verification results as JSON to PATH (used by make verify)",
    )
    group.addoption(
        "--verification-run",
        type=int,
        default=1,
        help="run number for repeated live runs (make verify-live RUNS=N)",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.stash[RESULTS_KEY] = []


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Probabilistic tests need a real model; skip them on the fake provider."""
    provider = os.environ.get("LLM_PROVIDER", "fake").strip().lower()
    if provider in LIVE_PROVIDERS_EXCLUDED:
        skip = pytest.mark.skip(
            reason="probabilistic: needs a real LLM_PROVIDER (make verify-live)"
        )
        for item in items:
            if item.get_closest_marker("probabilistic"):
                item.add_marker(skip)


def _meta(item: pytest.Item) -> dict[str, Any] | None:
    marker = item.get_closest_marker("verification")
    return marker.kwargs.get("meta") if marker else None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]):
    report = yield
    meta = _meta(item)
    if meta is None:
        return report
    # One record per test: the call phase, or setup when setup failed or skipped.
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        reason = ""
        if report.skipped and isinstance(report.longrepr, tuple):
            reason = str(report.longrepr[2])
        elif report.failed:
            reason = (
                report.longreprtext.strip().splitlines()[-1][:300] if report.longreprtext else ""
            )
        role_models = {
            k.removeprefix("LLM_MODEL_").lower(): v
            for k, v in os.environ.items()
            if k.startswith("LLM_MODEL_") and v
        }
        item.config.stash[RESULTS_KEY].append(
            {
                **meta,
                "nodeid": item.nodeid,
                "outcome": report.outcome,
                "reason": reason,
                "observed": getattr(item, "observed", ""),
                "evidence": getattr(item, "evidence", []),
                "duration_s": round(report.duration, 3),
                "provider": os.environ.get("LLM_PROVIDER", "fake"),
                "models": role_models,
                "run": item.config.getoption("--verification-run"),
                "finished_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )
    return report


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    path = session.config.getoption("--verification-results")
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    results = session.config.stash[RESULTS_KEY]
    out.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------- recording fixtures


@pytest.fixture
def observed(request: pytest.FixtureRequest) -> Callable[[str], None]:
    """observed("one line: what actually happened"). Shown in the report (B2 rule 6)."""

    def record(text: str) -> None:
        request.node.observed = " ".join(text.split())

    return record


@pytest.fixture
def evidence(request: pytest.FixtureRequest) -> Callable[[str, Any], None]:
    """evidence("audit_rows", rows): attach IDs, counts, codes. Never secrets or student text."""
    request.node.evidence = []

    def attach(label: str, value: Any) -> None:
        request.node.evidence.append({"label": label, "value": value})

    return attach


# ---------------------------------------------------------------- environment fixtures


@pytest.fixture
def live_only() -> None:
    """Skip unless LLM_PROVIDER names a real provider."""
    if os.environ.get("LLM_PROVIDER", "fake").strip().lower() in LIVE_PROVIDERS_EXCLUDED:
        pytest.skip("needs a real LLM_PROVIDER")


def _needs(module: str, task: str) -> Any:
    try:
        return importlib.import_module(module)
    except ModuleNotFoundError:
        pytest.skip(f"needs {module} ({task})")


@pytest.fixture
def fake_llm() -> Callable[[str], Any]:
    """fake_llm("script_name") installs FakeLLM with a script and returns its recorder (C1)."""
    llm = _needs("backend.llm.fake", "C1: FakeLLM")
    installer = getattr(llm, "install_for_test", None)
    if installer is None:
        pytest.skip("backend.llm.fake has no install_for_test(script) yet (C1)")
    return installer


@pytest.fixture
def agent_token() -> Callable[..., str]:
    """agent_token(kind, course_id=..., ...) mints a capability token (E5)."""
    tokens = _needs("backend.identity.tokens", "E5: capability tokens")
    return tokens.mint


@pytest.fixture
def api_client_factory() -> Callable[..., Any]:
    """as_student / as_instructor clients with real sessions, TOTP and CSRF (E4 + web app)."""
    _needs("backend.app.main", "web app and E4 identity")
    clients = _needs("tests.support.api_clients", "B: API client helpers, after E4")
    return clients.make_client


@pytest.fixture
def mailpit() -> Callable[[], list[dict[str, Any]]]:
    """Returns a function listing Mailpit messages (summary fields only)."""
    base = os.environ.get("MAILPIT_API", "http://127.0.0.1:8025/api/v1")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        opener.open(f"{base}/info", timeout=2).close()
    except OSError:
        pytest.skip("Mailpit is not reachable (make up)")

    def messages() -> list[dict[str, Any]]:
        with opener.open(f"{base}/messages", timeout=5) as resp:
            return json.load(resp).get("messages", [])

    return messages
