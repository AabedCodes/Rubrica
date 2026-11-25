"""Provision runtime roles and least-privilege grants (C31).

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

from backend.db.session import _read_password

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

ROLE_SECRETS = {
    "rubrica_web": "db_web_password",
    "rubrica_ingest": "db_ingest_password",
    "rubrica_grading": "db_grading_password",
    "rubrica_mcp": "db_mcp_password",
    "rubrica_release": "db_release_password",
    "rubrica_fetch": "db_fetch_password",
}

# Each tuple is (privilege, tables). Columns in parentheses restrict a grant.
GRANTS = {
    "rubrica_web": (
        ("SELECT", "users, courses, enrollments, assignments, proposed_grades, appeals, audit_log"),
        ("SELECT (id, course_id)", "blog_posts"),
        ("SELECT (id, student_id, assignment_id)", "submissions"),
        ("INSERT", "materials, submissions, blog_posts, blog_comments"),
        ("UPDATE (status, approved_by, approved_at)", "proposed_grades"),
    ),
    "rubrica_ingest": (
        ("SELECT", "materials"),
        ("INSERT", "material_chunks, blog_chunks"),
    ),
    "rubrica_grading": (
        (
            "SELECT",
            "submissions, assignments, rubric_criteria, answer_keys, "
            "material_chunks, web_snapshots",
        ),
        ("SELECT (id, assignment_id)", "grading_runs"),
        ("INSERT", "grading_results, citation_verdicts, orchestrator_transcripts"),
    ),
    "rubrica_mcp": (
        ("SELECT", "assignments, rubric_criteria, answer_keys, materials, material_chunks"),
        (
            "SELECT",
            "blog_posts, blog_comments, blog_chunks, grading_results, "
            "proposed_grades, appeals, drafts",
        ),
        ("SELECT (id, student_id, assignment_id)", "submissions"),
        ("SELECT (id, assignment_id)", "grading_runs"),
        ("INSERT", "proposed_grades, appeals, drafts, grade_change_proposals, manual_queue"),
    ),
    "rubrica_release": (
        ("SELECT", "proposed_grades, drafts"),
        ("SELECT (id, assignment_id)", "submissions"),
        ("SELECT (id, course_id, status)", "assignments, materials"),
        ("SELECT (id, material_id, course_id, visibility)", "material_chunks"),
        ("UPDATE (status)", "assignments, materials"),
        ("UPDATE (visibility)", "material_chunks"),
    ),
    "rubrica_fetch": (("INSERT", "web_snapshots"),),
}


def upgrade() -> None:
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC")
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute("SET LOCAL password_encryption = 'scram-sha-256'")
    op.execute("SET LOCAL log_parameter_max_length = 0")
    op.execute("SET LOCAL log_parameter_max_length_on_error = 0")
    op.execute("""
        CREATE FUNCTION pg_temp.create_runtime_role(role_name text, role_password text)
        RETURNS void LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            EXECUTE format(
                'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE '
                'NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD %L', role_name, role_password
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE EXCEPTION 'Could not provision database role %', role_name
                USING ERRCODE = SQLSTATE;
        END;
        $$;
    """)

    provision = sa.text("SELECT pg_temp.create_runtime_role(:role, :password)")
    for role, filename in ROLE_SECRETS.items():
        op.get_bind().execute(provision, {"role": role, "password": _read_password(filename)})
        op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
        op.execute(f"GRANT INSERT ON TABLE audit_log TO {role}")
        for privilege, tables in GRANTS[role]:
            op.execute(f"GRANT {privilege} ON TABLE {tables} TO {role}")
    op.execute("DROP FUNCTION pg_temp.create_runtime_role(text, text)")


def downgrade() -> None:
    for role, grants in GRANTS.items():
        for privilege, tables in grants:
            op.execute(f"REVOKE {privilege} ON TABLE {tables} FROM {role}")
        op.execute(f"REVOKE INSERT ON TABLE audit_log FROM {role}")
        op.execute(f"REVOKE USAGE ON SCHEMA public FROM {role}")
        op.execute(f"DROP ROLE {role}")
