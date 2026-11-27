"""T-19: a leaked service credential opens only what that service needs (blast radius)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.db import SessionContext
from tests.verification.framework import verification

# The gitleaks half of T-19 (a CANARY-T19 fake key in a fixture is reported)
# lands with E8's `secrets` CI job; this test covers the database half.


@verification(
    threat="T-19",
    control=["C12", "C31"],
    location=(
        "backend/db/migrations/versions/0002_roles.py:GRANTS; "
        "backend/db/migrations/versions/0003_row_security.py; deploy/docker-compose.yml"
    ),
    canary="input: connect as rubrica_ingest (as if its password leaked) and read coursework",
    expected=(
        "The ingest credential reads no submissions, grades or answer keys (permission "
        "denied), and cannot write audit history."
    ),
)
def test_t19_ingest_credential_cannot_read_coursework(rubrica_db, observed, evidence):
    w = rubrica_db
    results = {}
    for table in ("submissions", "proposed_grades", "answer_keys", "users"):
        try:
            with w.as_role("rubrica_ingest", SessionContext("system")) as db:
                db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))  # noqa: S608 (fixed names)
            results[table] = "readable"
        except DBAPIError as exc:
            results[table] = getattr(exc.orig, "sqlstate", "error")
    with (
        pytest.raises(DBAPIError) as exc,
        w.as_role("rubrica_ingest", SessionContext("system")) as db,
    ):
        db.execute(text("DELETE FROM audit_log"))
    results["audit_log delete"] = getattr(exc.value.orig, "sqlstate", "error")

    evidence("sqlstate_by_table", results)
    observed("; ".join(f"{k}: {v}" for k, v in results.items()))
    assert all(v == "42501" for v in results.values()), results
