"""Unit tests for scripts/check_pins.py (C16, T-17)."""

from pathlib import Path

import check_pins as cp

SHA = "3d3c42e5aac5ba805825da76410c181273ba90b1"
DIGEST = "sha256:" + "a" * 64
REPO_ROOT = Path(__file__).resolve().parents[2]


def make_repo(tmp_path: Path, *, workflow: str, compose: str, dockerfile: str) -> Path:
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(workflow)
    (tmp_path / "deploy").mkdir()
    (tmp_path / "deploy" / "docker-compose.yml").write_text(compose)
    (tmp_path / "deploy" / "app.Dockerfile").write_text(dockerfile)
    (tmp_path / "backend").mkdir()
    (tmp_path / "backend" / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "backend" / "uv.lock").write_text("")
    return tmp_path


def test_pinned_repo_passes(tmp_path):
    root = make_repo(
        tmp_path,
        workflow=f"steps:\n  - uses: actions/checkout@{SHA} # v7.0.1\n  - uses: ./local-action\n",
        compose=f"services:\n  db:\n    image: postgres@{DIGEST}\n  web:\n    build: .\n",
        dockerfile=(
            f"FROM python:3.13-slim@{DIGEST} AS base\n"
            f"COPY --from=ghcr.io/astral-sh/uv:0.13.9@{DIGEST} /uv /bin/uv\n"
            "FROM base AS final\nCOPY --from=base /app /app\n"
        ),
    )
    assert cp.check(root) == []
    assert cp.main([str(root)]) == 0


def test_unpinned_action_and_image_fail(tmp_path):
    # T-17 canary inputs: a tag-pinned action and a tag-only image.
    root = make_repo(
        tmp_path,
        workflow="steps:\n  - uses: actions/checkout@v4\n  - uses: 'actions/setup-node@main'\n",
        compose="services:\n  db:\n    image: postgres:18\n",
        dockerfile="FROM python:3.13-slim\nCOPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv\n",
    )
    messages = [str(f) for f in cp.check(root)]
    assert len(messages) == 5, messages
    assert any("actions/checkout@v4" in m for m in messages)
    assert any("actions/setup-node@main" in m for m in messages)
    assert any("postgres:18" in m for m in messages)
    assert any("FROM not pinned" in m for m in messages)
    assert any("uv:latest" in m for m in messages)
    assert cp.main([str(root)]) == 1


def test_short_sha_is_not_a_pin(tmp_path):
    root = make_repo(
        tmp_path,
        workflow="steps:\n  - uses: actions/checkout@3d3c42e\n",
        compose="services: {}\n",
        dockerfile="FROM scratch\n",
    )
    assert len(cp.check(root)) == 1


def test_missing_lockfiles(tmp_path):
    root = make_repo(tmp_path, workflow="", compose="", dockerfile="FROM scratch\n")
    (root / "backend" / "uv.lock").unlink()
    (root / "frontend").mkdir()
    (root / "frontend" / "package.json").write_text("{}")
    paths = sorted(f.path for f in cp.check(root))
    assert paths == ["backend/uv.lock", "frontend/package-lock.json"]


def test_this_repository_is_pinned():
    findings = cp.check(REPO_ROOT)
    assert findings == [], "\n".join(map(str, findings))
