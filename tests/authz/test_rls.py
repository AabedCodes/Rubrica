"""Row-level security suite (B4, C31, T-23).

Connects to a real PostgreSQL as each runtime role, through the same
`backend.db.session()` helper the services use, and checks what each role
can and can't see or change. The ownership filter that application code would
normally add is deliberately left out of every query: the point is that the
database still holds when the code has a bug.

Complements D1's tests/authz/test_d1_database.py (which exercises D's service
functions). This suite queries the tables directly and also checks the
catalog: every table has RLS forced, and no runtime role can bypass it.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.db import SessionContext
from backend.db.session import RUNTIME_ROLES
from tests.support.db import KEY_TEXT

INSUFFICIENT_PRIVILEGE = "42501"
RLS_TABLES = [
    "users",
    "courses",
    "enrollments",
    "assignments",
    "rubric_criteria",
    "answer_keys",
    "materials",
    "material_chunks",
    "blog_posts",
    "blog_comments",
    "blog_chunks",
    "submissions",
    "grading_runs",
    "grading_results",
    "proposed_grades",
    "web_snapshots",
    "citation_verdicts",
    "appeals",
    "grade_change_proposals",
    "drafts",
    "manual_queue",
    "chat_transcripts",
    "orchestrator_transcripts",
    "audit_log",
]


def ctx_student(w, name="alice", course="course1"):
    return SessionContext("student", user_id=w.ids[name], course_id=w.ids[course])


def ctx_instructor(w, name="instructor1", course="course1"):
    return SessionContext("instructor", user_id=w.ids[name], course_id=w.ids[course])


def ctx_run(w, run="run1", course="course1"):
    return SessionContext("grading_run", run_id=w.ids[run], course_id=w.ids[course])


def ids(db, sql):
    return set(db.execute(text(sql)).scalars().all())


def denied(exc_info) -> bool:
    return getattr(exc_info.value.orig, "sqlstate", None) == INSUFFICIENT_PRIVILEGE


# ---------------------------------------------------------------- catalog checks


def test_every_data_table_forces_row_level_security(rubrica_db):
    with rubrica_db.owner.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class "
                "WHERE relnamespace = 'public'::regnamespace AND relkind = 'r' "
                "AND relname = ANY(:t)"
            ),
            {"t": RLS_TABLES},
        ).all()
    found = {r.relname: (r.relrowsecurity, r.relforcerowsecurity) for r in rows}
    assert set(found) == set(RLS_TABLES), f"missing tables: {set(RLS_TABLES) - set(found)}"
    assert all(enabled and forced for enabled, forced in found.values()), found


def test_no_runtime_role_can_bypass_rls_or_escalate(rubrica_db):
    with rubrica_db.owner.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT rolname, rolsuper, rolbypassrls, rolcreaterole, rolcreatedb, rolinherit "
                "FROM pg_roles WHERE rolname = ANY(:r)"
            ),
            {"r": list(RUNTIME_ROLES)},
        ).all()
    assert {r.rolname for r in rows} == set(RUNTIME_ROLES)
    for r in rows:
        assert not (r.rolsuper or r.rolbypassrls or r.rolcreaterole or r.rolcreatedb), r.rolname


def test_no_runtime_role_may_change_or_delete_audit_rows_by_grant(rubrica_db):
    with rubrica_db.owner.connect() as conn:
        bad = conn.execute(
            text(
                "SELECT grantee, privilege_type FROM information_schema.role_table_grants "
                "WHERE table_name = 'audit_log' AND grantee = ANY(:r) "
                "AND privilege_type IN ('UPDATE', 'DELETE', 'TRUNCATE')"
            ),
            {"r": list(RUNTIME_ROLES)},
        ).all()
    assert bad == []


# ---------------------------------------------------------------- rubrica_mcp (process 6)


def test_mcp_as_student_sees_only_own_released_grades(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_mcp", ctx_student(w)) as db:
        visible = ids(db, "SELECT id FROM proposed_grades")
    assert visible == {w.ids["g_alice_a1_released"]}


def test_mcp_as_student_reads_no_answer_keys(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_mcp", ctx_student(w)) as db:
        assert db.execute(text("SELECT count(*) FROM answer_keys")).scalar() == 0
        hits = db.execute(
            text("SELECT count(*) FROM answer_keys WHERE content = :k"), {"k": KEY_TEXT}
        ).scalar()
    assert hits == 0


def test_mcp_as_student_sees_no_other_course_rows(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_mcp", ctx_student(w)) as db:
        assignments = ids(db, "SELECT id FROM assignments")
        chunks = ids(db, "SELECT id FROM blog_chunks")
    assert w.ids["a3"] not in assignments
    assert w.ids["chunk_post_c2"] not in chunks


def test_mcp_as_student_with_wrong_course_still_sees_only_own_grades(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_mcp", ctx_student(w, "alice", "course2")) as db:
        visible = ids(db, "SELECT id FROM proposed_grades")
    assert w.ids["g_carol_a3_released"] not in visible


# FINDING-B4-01 (28 Nov): rubrica_mcp policies scope rows to the token's course
# (`course_id = rubrica.course_id`) but don't check that the user is enrolled
# in that course (the `_member()` helper in 0003 is unused there). The token
# minting in the web app is then the only check; C31 says to re-check at the
# resource. strict xfail: when D adds the enrollment check these XPASS and
# fail, so the marker gets removed and the tests become ordinary guards.
ENROLLMENT_GAP = pytest.mark.xfail(
    strict=True, reason="FINDING-B4-01: MCP RLS doesn't check enrollment (owner D)"
)


@ENROLLMENT_GAP
def test_mcp_student_not_enrolled_in_token_course_sees_none_of_its_assignments(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_mcp", ctx_student(w, "alice", "course2")) as db:
        assignments = ids(db, "SELECT id FROM assignments")
    assert w.ids["a3"] not in assignments


@ENROLLMENT_GAP
def test_mcp_instructor_not_enrolled_in_token_course_sees_none_of_its_grades_or_keys(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_mcp", ctx_instructor(w, "instructor1", "course2")) as db:
        grades = ids(db, "SELECT id FROM proposed_grades")
        subs = ids(db, "SELECT id FROM submissions")
    assert w.ids["g_carol_a3_released"] not in grades
    assert w.ids["s_carol_a3"] not in subs


def test_mcp_cannot_release_a_grade(rubrica_db):
    w = rubrica_db
    with pytest.raises(DBAPIError) as exc, w.as_role("rubrica_mcp", ctx_instructor(w)) as db:
        db.execute(text("UPDATE proposed_grades SET status = 'released'"))
    assert denied(exc)


# ---------------------------------------------------------------- rubrica_grading (process 2)


def test_grading_run_reads_only_its_assignment(rubrica_db):
    w = rubrica_db
    with w.as_role("rubrica_grading", ctx_run(w)) as db:
        subs = ids(db, "SELECT id FROM submissions")
        keys = ids(db, "SELECT assignment_id FROM answer_keys")
    assert subs == {w.ids["s_alice_a1"], w.ids["s_bob_a1"]}
    assert keys <= {w.ids["a1"]}


def test_grading_has_no_access_to_blog_tables(rubrica_db):
    w = rubrica_db
    for table in ("blog_chunks", "blog_posts", "blog_comments"):
        with pytest.raises(DBAPIError) as exc, w.as_role("rubrica_grading", ctx_run(w)) as db:
            db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))  # noqa: S608 (fixed table names)
        assert denied(exc), table


# ---------------------------------------------------------------- rubrica_ingest (process 5)


@pytest.mark.parametrize("table", ["submissions", "proposed_grades", "answer_keys"])
def test_ingest_cannot_read_student_or_grade_data(rubrica_db, table):
    w = rubrica_db
    ctx = SessionContext("system")
    with pytest.raises(DBAPIError) as exc, w.as_role("rubrica_ingest", ctx) as db:
        db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))  # noqa: S608 (fixed table names)
    assert denied(exc)


# ---------------------------------------------------------------- every role


@pytest.mark.parametrize("role", sorted(RUNTIME_ROLES))
@pytest.mark.parametrize(
    "statement", ["UPDATE audit_log SET action = action", "DELETE FROM audit_log"]
)
def test_audit_log_is_append_only_for_every_role(rubrica_db, role, statement):
    w = rubrica_db
    with pytest.raises(DBAPIError) as exc, w.as_role(role, SessionContext("system")) as db:
        db.execute(text(statement))
    assert denied(exc)


@pytest.mark.parametrize(
    ("role", "table"),
    [
        ("rubrica_mcp", "proposed_grades"),
        ("rubrica_mcp", "assignments"),
        ("rubrica_mcp", "answer_keys"),
        ("rubrica_mcp", "blog_chunks"),
        ("rubrica_web", "proposed_grades"),
        ("rubrica_web", "assignments"),
        ("rubrica_grading", "submissions"),
        ("rubrica_grading", "answer_keys"),
        ("rubrica_release", "proposed_grades"),
    ],
)
def test_no_rls_context_means_no_rows(rubrica_db, role, table):
    """Fail closed: a connection that never set rubrica.* settings sees nothing."""
    with rubrica_db.raw(role) as conn:
        count = conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()  # noqa: S608
    assert count == 0
