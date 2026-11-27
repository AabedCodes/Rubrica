"""T-23: code drops the ownership filter; the database still returns only the caller's rows."""

from sqlalchemy import text

from backend.db import SessionContext
from tests.verification.framework import verification


@verification(
    threat="T-23",
    control=["C31", "C03", "C21"],
    location=(
        "backend/db/migrations/versions/0003_row_security.py:_mcp_policies; "
        "backend/db/session.py:session"
    ),
    canary=(
        "input: SELECT * FROM proposed_grades with no WHERE clause, run as rubrica_mcp "
        "for student alice (simulates the missing-filter bug)"
    ),
    expected=(
        "Only alice's own released grade comes back: not bob's released grade in the same "
        "course, not her own pending grade, not another course's grade."
    ),
)
def test_t23_query_without_ownership_filter(rubrica_db, observed, evidence):
    w = rubrica_db
    ctx = SessionContext("student", user_id=w.ids["alice"], course_id=w.ids["course1"])
    with w.as_role("rubrica_mcp", ctx) as db:
        rows = db.execute(text("SELECT id, status FROM proposed_grades")).all()

    seen = {r.id for r in rows}
    total = 4  # seeded proposed grades across both courses
    evidence("rows_returned", len(rows))
    evidence("rows_in_table", total)
    observed(
        f"{len(rows)} of {total} proposed grades returned; "
        f"own released={w.ids['g_alice_a1_released'] in seen}, "
        f"bob's={w.ids['g_bob_a1_released'] in seen}, "
        f"own pending={w.ids['g_alice_a2_pending'] in seen}, "
        f"other course={w.ids['g_carol_a3_released'] in seen}"
    )
    assert seen == {w.ids["g_alice_a1_released"]}
    assert all(r.status == "released" for r in rows)
