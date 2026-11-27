"""T-16: a package name an AI assistant invented is refused before install."""

import admission_check as ac
from tests.verification.framework import verification

NONEXISTENT = "rubrica-canary-t16-gradebook-mcp-tools"  # constructed name, never published


@verification(
    threat="T-16",
    control="C14",
    location="scripts/admission_check.py:check; .github/pull_request_template.md",
    canary=f"input: admission_check.py pypi {NONEXISTENT} (a name that does not exist)",
    expected=(
        "FAIL with 'does not exist'; a near-miss of a real package also suggests the real name."
    ),
)
def test_t16_nonexistent_package_fails(observed, evidence):
    # The registry answers 404 for an unknown name; the fetcher returns None for 404.
    gone = ac.check("pypi", NONEXISTENT, fetch=lambda url: None, known={"fastapi", "requests"})
    typo = ac.check("pypi", "reqeusts", fetch=lambda url: None, known={"fastapi", "requests"})
    evidence("verdicts", {"nonexistent": gone.verdict, "typo": typo.verdict})
    observed(
        f"{NONEXISTENT}: {gone.verdict} ({gone.reasons[0]}); "
        f"reqeusts: {typo.verdict} ({'; '.join(typo.reasons)})"
    )
    assert gone.verdict == ac.FAIL and "does not exist" in gone.reasons[0]
    assert typo.verdict == ac.FAIL and any("requests" in r for r in typo.reasons)
