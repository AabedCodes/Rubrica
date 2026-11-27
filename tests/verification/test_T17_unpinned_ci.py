"""T-17: a tag-pinned CI action or an image without a digest fails the build."""

import check_pins as cp
from tests.verification.framework import verification


@verification(
    threat="T-17",
    control="C16",
    location="scripts/check_pins.py:check; .github/workflows/ci.yml",
    canary=(
        "input: fixture workflow with 'uses: actions/checkout@v4', a service image "
        "'postgres:18', and a Dockerfile 'FROM python:3.13-slim'"
    ),
    expected="check_pins reports all three and exits 1; the real repository passes.",
)
def test_t17_unpinned_action_and_images_fail(tmp_path, observed, evidence):
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "jobs:\n  t:\n    services:\n      db:\n        image: postgres:18\n"
        "    steps:\n      - uses: actions/checkout@v4\n"
    )
    (tmp_path / "Dockerfile").write_text("FROM python:3.13-slim\n")
    findings = [str(f) for f in cp.check(tmp_path)]
    exit_code = cp.main([str(tmp_path)])
    real = cp.check(cp.Path(__file__).resolve().parents[2])

    evidence("findings", findings)
    observed(
        f"{len(findings)} unpinned items reported, exit {exit_code}; "
        f"real repo findings: {len(real)}"
    )
    assert exit_code == 1
    assert any("actions/checkout@v4" in f for f in findings)
    assert any("postgres:18" in f for f in findings)
    assert any("FROM not pinned" in f for f in findings)
    assert real == []
