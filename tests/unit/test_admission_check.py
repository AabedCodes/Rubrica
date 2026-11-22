"""Unit tests for scripts/admission_check.py (C14, T-16). Offline: registry replies are fixtures."""

import os
from datetime import UTC, datetime, timedelta

import pytest

import admission_check as ac

NOW = datetime(2026, 11, 22, tzinfo=UTC)
KNOWN_PYPI = {"requests", "fastapi", "pyotp", "numpy"}


def _iso(days_ago: int) -> str:
    return (NOW - timedelta(days=days_ago)).isoformat()


def pypi_doc(name="pyotp", releases=10, first_days_ago=2000, project_urls=None, version_days=None):
    rel = {}
    for i in range(releases):
        days = (
            first_days_ago - i * 30
            if i < releases - 1
            else (version_days if version_days is not None else max(first_days_ago - i * 30, 0))
        )
        rel[f"1.{i}.0"] = [{"upload_time_iso_8601": _iso(max(days, 0))}]
    return {
        "info": {
            "name": name,
            "summary": "Python One Time Password Library",
            "version": f"1.{releases - 1}.0",
            "author": "Synthetic Author, Second Author",
            "project_urls": project_urls
            if project_urls is not None
            else {"Source": f"https://github.com/example/{name}/tree/main"},
        },
        "releases": rel,
    }


def fetch_from(doc):
    return lambda url: doc


def run(name, doc, version=None, known=KNOWN_PYPI):
    return ac.check("pypi", name, version, fetch=fetch_from(doc), known=known, now=NOW)


def test_credible_package_passes():
    r = run("pyotp", pypi_doc())
    assert r.verdict == ac.PASS
    assert r.info.source_repo == "https://github.com/example/pyotp"
    assert r.info.maintainers == ["Synthetic Author", "Second Author"]


def test_nonexistent_package_fails():
    # T-16: a name an assistant invented. The registry returns 404 -> fetcher returns None.
    r = run("fastapi-gradebook-mcp-tools", None)
    assert r.verdict == ac.FAIL
    assert "does not exist" in r.reasons[0]


def test_nonexistent_typo_suggests_real_name():
    r = run("reqeusts", None)
    assert r.verdict == ac.FAIL
    assert any("requests" in reason for reason in r.reasons)


def test_existing_lookalike_needs_review():
    r = run("fastapl", pypi_doc(name="fastapl"))
    assert r.verdict == ac.REVIEW
    assert any("fastapi" in reason for reason in r.reasons)


def test_known_name_is_not_its_own_lookalike():
    assert ac.lookalikes("pypi", "FastAPI", KNOWN_PYPI) == []
    assert ac.lookalikes("pypi", "py_otp", {"py-otp"}) == []  # PEP 503 normalisation


def test_young_package_needs_review():
    r = run("brandnew", pypi_doc(name="brandnew", releases=6, first_days_ago=30))
    assert r.verdict == ac.REVIEW
    assert any("days ago" in reason for reason in r.reasons)


def test_few_releases_need_review():
    r = run("tiny", pypi_doc(name="tiny", releases=2))
    assert r.verdict == ac.REVIEW
    assert any("release(s)" in reason for reason in r.reasons)


def test_missing_source_repo_needs_review():
    r = run(
        "nosource",
        pypi_doc(name="nosource", project_urls={"Docs": "https://docs.example"}),
    )
    assert r.verdict == ac.REVIEW
    assert any("source repository" in reason for reason in r.reasons)


def test_unknown_version_fails():
    r = run("pyotp", pypi_doc(), version="99.0.0")
    assert r.verdict == ac.FAIL


def test_fresh_version_needs_review():
    doc = pypi_doc(releases=10, version_days=3)
    r = run("pyotp", doc, version="1.9.0")
    assert r.verdict == ac.REVIEW
    assert any("published only 3 days ago" in reason for reason in r.reasons)


def test_npm_scoped_package_and_repo_url():
    doc = {
        "name": "@vitejs/plugin-react",
        "description": "plugin",
        "dist-tags": {"latest": "5.0.0"},
        "versions": {f"{i}.0.0": {} for i in range(1, 8)},
        "time": {
            "created": _iso(1500),
            **{f"{i}.0.0": _iso(1500 - i * 50) for i in range(1, 8)},
        },
        "maintainers": [{"name": "synthetic-maintainer"}],
        "repository": {"url": "git+https://github.com/vitejs/vite-plugin-react.git"},
    }
    urls = []

    def fetch(url):
        urls.append(url)
        return doc

    r = ac.check("npm", "@vitejs/plugin-react", fetch=fetch, known=set(), now=NOW)
    assert r.verdict == ac.PASS
    assert urls == ["https://registry.npmjs.org/@vitejs%2Fplugin-react"]
    assert r.info.source_repo == "https://github.com/vitejs/vite-plugin-react"


def test_edit_distance():
    assert ac.edit_distance("requests", "requests") == 0
    assert ac.edit_distance("reqeusts", "requests") == 1  # transposition
    assert ac.edit_distance("request", "requests") == 1
    assert ac.edit_distance("numpy", "nunpyy") == 2


def test_exit_codes_and_report():
    r = run("pyotp", pypi_doc())
    text = ac.report("pypi", "pyotp", None, r)
    assert text.splitlines()[1] == "RESULT: PASS"
    assert ac.EXIT_CODES == {"PASS": 0, "FAIL": 1, "REVIEW": 2}


@pytest.mark.network
@pytest.mark.skipif(os.environ.get("RUBRICA_NETWORK_TESTS") != "1", reason="network test")
def test_live_registry_nonexistent_name():
    r = ac.check("pypi", "rubrica-canary-t16-0000-does-not-exist")
    assert r.verdict == ac.FAIL
