"""Enforce course, student and grading-run boundaries in PostgreSQL (C31).

Revision ID: 0003
Revises: 0002
"""

# Policy DDL interpolates only static SQL fragments defined in this revision.
# ruff: noqa: S608
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = (
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
    "sessions",
    "capability_tokens",
    "alerts",
    "course_controls",
    "jobs",
)
ROLES = ("web", "ingest", "grading", "mcp", "release", "fetch")

ACTOR = "current_setting('rubrica.actor_kind', true)"
USER = "NULLIF(current_setting('rubrica.user_id', true), '')::uuid"
COURSE = "NULLIF(current_setting('rubrica.course_id', true), '')::uuid"
RUN = "NULLIF(current_setting('rubrica.run_id', true), '')::uuid"

STUDENT = f"{ACTOR} = 'student' AND {USER} IS NOT NULL"
INSTRUCTOR = f"{ACTOR} = 'instructor' AND {USER} IS NOT NULL"
DELEGATE = f"({STUDENT} OR {INSTRUCTOR})"
SYSTEM = f"{ACTOR} = 'system'"
GRADING = f"{ACTOR} = 'grading_run' AND {RUN} IS NOT NULL"
SCOPED_COURSE = f"course_id = {COURSE}"
RUN_ASSIGNMENT = f"SELECT r.assignment_id FROM grading_runs r WHERE r.id = {RUN}"


def _member(course: str) -> str:
    return (
        f"EXISTS (SELECT 1 FROM enrollments e WHERE e.course_id = {course} "
        f"AND e.user_id = {USER} AND e.role = {ACTOR})"
    )


def _assignment(table: str, condition: str = "true") -> str:
    return (
        f"EXISTS (SELECT 1 FROM assignments a WHERE a.id = {table}.assignment_id AND ({condition}))"
    )


def _submission(table: str, condition: str = "true") -> str:
    return (
        f"EXISTS (SELECT 1 FROM submissions s WHERE s.id = {table}.submission_id AND ({condition}))"
    )


def _post(table: str) -> str:
    return (
        f"EXISTS (SELECT 1 FROM blog_posts p WHERE p.id = {table}.post_id "
        f"AND p.course_id = {COURSE})"
    )


def _create_policy(table: str, role: str, operation: str, using: str = "", check: str = "") -> None:
    sql = f"CREATE POLICY {role}_{operation.lower()} ON {table} FOR {operation} TO rubrica_{role}"
    if using:
        sql += f" USING ({using})"
    if check:
        sql += f" WITH CHECK ({check})"
    op.execute(sql)


def _create_policy_functions() -> None:
    # These checks give insert-only services a boolean tying rows to verified
    # context and source metadata, without granting them reads of source tables.
    op.execute(f"""
        CREATE FUNCTION public.fetch_submission_in_run(wanted_submission uuid)
        RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.submissions s
                JOIN public.assignments a ON a.id = s.assignment_id
                JOIN public.grading_runs r ON r.assignment_id = a.id
                WHERE s.id = wanted_submission AND r.id = {RUN} AND a.course_id = {COURSE}
            );
        $$;
    """)
    op.execute("""
        CREATE FUNCTION public.blog_chunk_source_matches(
            wanted_origin text, wanted_id uuid, wanted_course uuid, wanted_author uuid
        )
        RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog AS $$
            SELECT CASE wanted_origin
                WHEN 'post' THEN EXISTS (
                    SELECT 1 FROM public.blog_posts p
                    WHERE p.id = wanted_id AND p.course_id = wanted_course
                      AND p.author_id = wanted_author
                )
                WHEN 'comment' THEN EXISTS (
                    SELECT 1 FROM public.blog_comments c
                    JOIN public.blog_posts p ON p.id = c.post_id
                    WHERE c.id = wanted_id AND p.course_id = wanted_course
                      AND c.author_id = wanted_author
                )
                ELSE false
            END;
        $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION public.fetch_submission_in_run(uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.fetch_submission_in_run(uuid) TO rubrica_fetch")
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "public.blog_chunk_source_matches(text, uuid, uuid, uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.blog_chunk_source_matches(text, uuid, uuid, uuid) "
        "TO rubrica_ingest"
    )


def _web_policies() -> None:
    scoped_member = f"{DELEGATE} AND {SCOPED_COURSE} AND {_member(COURSE)}"
    scoped_instructor = f"{INSTRUCTOR} AND {SCOPED_COURSE} AND {_member(COURSE)}"
    _create_policy("users", "web", "SELECT", f"{SYSTEM} OR ({DELEGATE} AND id = {USER})")
    _create_policy("enrollments", "web", "SELECT", f"{DELEGATE} AND user_id = {USER}")
    _create_policy("courses", "web", "SELECT", f"{DELEGATE} AND {_member('courses.id')}")
    _create_policy(
        "assignments",
        "web",
        "SELECT",
        f"{scoped_member} AND ({INSTRUCTOR} OR status = 'published')",
    )
    _create_policy(
        "materials",
        "web",
        "INSERT",
        check=f"{scoped_instructor} AND uploader_id = {USER} AND status = 'pending'",
    )
    own_submission = f"{STUDENT} AND student_id = {USER} AND {_assignment('submissions')}"
    _create_policy("submissions", "web", "INSERT", check=own_submission)
    _create_policy(
        "submissions",
        "web",
        "SELECT",
        f"({INSTRUCTOR} OR ({STUDENT} AND student_id = {USER})) AND {_assignment('submissions')}",
    )
    _create_policy("blog_posts", "web", "SELECT", scoped_member)
    _create_policy(
        "blog_posts", "web", "INSERT", check=f"{scoped_instructor} AND author_id = {USER}"
    )
    _create_policy(
        "blog_comments",
        "web",
        "INSERT",
        check=f"{DELEGATE} AND author_id = {USER} AND {_post('blog_comments')}",
    )

    managed_grade = f"{INSTRUCTOR} AND {_submission('proposed_grades')}"
    _create_policy("proposed_grades", "web", "SELECT", managed_grade)
    # The web approval handler must verify re-authentication before it opens
    # this context. The database constrains which row and state may be changed.
    _create_policy(
        "proposed_grades",
        "web",
        "UPDATE",
        f"{managed_grade} AND status = 'pending'",
        f"{managed_grade} AND status = 'approved' AND approved_by = {USER} "
        "AND approved_at IS NOT NULL AND released_at IS NULL",
    )
    _create_policy("appeals", "web", "SELECT", f"{INSTRUCTOR} AND {_submission('appeals')}")
    _create_policy("audit_log", "web", "SELECT", scoped_instructor)


def _ingestion_policies() -> None:
    scoped_job = f"{SYSTEM} AND {SCOPED_COURSE}"
    _create_policy("materials", "ingest", "SELECT", scoped_job)
    _create_policy(
        "material_chunks",
        "ingest",
        "INSERT",
        check=f"{scoped_job} AND EXISTS (SELECT 1 FROM materials m "
        "WHERE m.id = material_chunks.material_id AND m.course_id = material_chunks.course_id "
        "AND m.status = material_chunks.visibility)",
    )
    _create_policy(
        "blog_chunks",
        "ingest",
        "INSERT",
        check=f"{scoped_job} AND "
        "public.blog_chunk_source_matches(origin, origin_id, course_id, author_id)",
    )


def _grading_policies() -> None:
    _create_policy("grading_runs", "grading", "SELECT", f"{GRADING} AND id = {RUN}")
    _create_policy(
        "assignments",
        "grading",
        "SELECT",
        f"{GRADING} AND {SCOPED_COURSE} AND id IN ({RUN_ASSIGNMENT})",
    )
    for table in ("submissions", "rubric_criteria", "answer_keys"):
        visible = _assignment(table)
        if table == "answer_keys":
            visible += " AND status = 'approved'"
        _create_policy(table, "grading", "SELECT", visible)

    _create_policy(
        "material_chunks",
        "grading",
        "SELECT",
        "visibility = 'published' AND EXISTS (SELECT 1 FROM assignments a "
        "WHERE a.course_id = material_chunks.course_id)",
    )
    _create_policy("web_snapshots", "grading", "SELECT", _submission("web_snapshots"))
    _create_policy(
        "grading_results",
        "grading",
        "INSERT",
        check=f"{GRADING} AND run_id = {RUN} AND {_submission('grading_results')}",
    )
    _create_policy(
        "citation_verdicts",
        "grading",
        "INSERT",
        check="EXISTS (SELECT 1 FROM web_snapshots w WHERE w.id = citation_verdicts.snapshot_id)",
    )
    _create_policy(
        "orchestrator_transcripts",
        "grading",
        "INSERT",
        check=f"{GRADING} AND run_id = {RUN} AND EXISTS (SELECT 1 FROM assignments)",
    )


def _mcp_policies() -> None:
    _create_policy("grading_runs", "mcp", "SELECT", f"{GRADING} AND id = {RUN}")
    _create_policy(
        "assignments",
        "mcp",
        "SELECT",
        f"{SCOPED_COURSE} AND ({INSTRUCTOR} OR ({STUDENT} AND status = 'published') "
        f"OR ({GRADING} AND id IN ({RUN_ASSIGNMENT})))",
    )
    _create_policy("rubric_criteria", "mcp", "SELECT", _assignment("rubric_criteria"))
    _create_policy("answer_keys", "mcp", "SELECT", f"{INSTRUCTOR} AND {_assignment('answer_keys')}")
    _create_policy(
        "submissions",
        "mcp",
        "SELECT",
        f"{_assignment('submissions')} AND ({INSTRUCTOR} OR {GRADING} "
        f"OR ({STUDENT} AND student_id = {USER}))",
    )
    for table in ("materials", "material_chunks", "blog_posts", "blog_chunks"):
        visible = f"{DELEGATE} AND {SCOPED_COURSE}"
        if table == "materials":
            visible += " AND status = 'published'"
        if table == "material_chunks":
            visible += " AND visibility = 'published'"
        _create_policy(table, "mcp", "SELECT", visible)
    _create_policy("blog_comments", "mcp", "SELECT", f"{DELEGATE} AND {_post('blog_comments')}")

    _create_policy(
        "proposed_grades",
        "mcp",
        "SELECT",
        f"{_submission('proposed_grades')} AND "
        f"({INSTRUCTOR} OR ({STUDENT} AND status = 'released') "
        f"OR ({GRADING} AND status = 'pending'))",
    )
    _create_policy(
        "grading_results",
        "mcp",
        "SELECT",
        f"{_submission('grading_results')} AND ({INSTRUCTOR} OR ({GRADING} AND run_id = {RUN}) "
        f"OR ({STUDENT} AND validator_status <> 'rejected' AND EXISTS ("
        "SELECT 1 FROM proposed_grades g WHERE g.submission_id = grading_results.submission_id "
        "AND g.status = 'released' AND grading_results.id = ANY(g.result_ids))))",
    )
    _create_policy(
        "proposed_grades",
        "mcp",
        "INSERT",
        check=f"{GRADING} AND {_submission('proposed_grades')} AND status = 'pending' "
        "AND approved_by IS NULL AND approved_at IS NULL AND released_at IS NULL",
    )

    _create_policy("appeals", "mcp", "SELECT", f"{DELEGATE} AND {_submission('appeals')}")
    _create_policy(
        "appeals",
        "mcp",
        "INSERT",
        check=f"{STUDENT} AND student_id = {USER} AND status = 'open' AND EXISTS ("
        "SELECT 1 FROM proposed_grades g WHERE g.submission_id = appeals.submission_id "
        "AND g.status = 'released')",
    )
    _create_policy(
        "grade_change_proposals",
        "mcp",
        "INSERT",
        check=f"{INSTRUCTOR} AND status = 'pending' AND decided_by IS NULL AND decided_at IS NULL "
        "AND EXISTS (SELECT 1 FROM appeals ap WHERE ap.id = grade_change_proposals.appeal_id "
        "AND ap.status = 'open')",
    )
    _create_policy(
        "manual_queue",
        "mcp",
        "INSERT",
        check=f"{GRADING} AND {_submission('manual_queue')} "
        "AND resolved_by IS NULL AND resolved_at IS NULL",
    )
    _create_policy("drafts", "mcp", "SELECT", f"{INSTRUCTOR} AND {SCOPED_COURSE}")
    _create_policy(
        "drafts", "mcp", "INSERT", check=f"{INSTRUCTOR} AND {SCOPED_COURSE} AND status = 'pending'"
    )


def _release_policies() -> None:
    scoped_instructor = f"{INSTRUCTOR} AND {SCOPED_COURSE}"
    for table, field, before in (
        ("assignments", "status", "draft"),
        ("materials", "status", "pending"),
        ("material_chunks", "visibility", "pending"),
    ):
        _create_policy(table, "release", "SELECT", scoped_instructor)
        after = f"{scoped_instructor} AND {field} = 'published'"
        if table == "material_chunks":
            after += (
                " AND EXISTS (SELECT 1 FROM materials m WHERE m.id = material_chunks.material_id "
                "AND m.status = 'published')"
            )
        _create_policy(
            table, "release", "UPDATE", f"{scoped_instructor} AND {field} = '{before}'", after
        )
    _create_policy("submissions", "release", "SELECT", _assignment("submissions"))
    _create_policy("drafts", "release", "SELECT", scoped_instructor)
    managed_grade = f"{INSTRUCTOR} AND {_submission('proposed_grades')}"
    approved = f"{managed_grade} AND status = 'approved'"
    _create_policy("proposed_grades", "release", "SELECT", approved)
    # PostgreSQL checks SELECT visibility on the updated row when the update
    # targets a row by ID. Release stays readable only while approved.
    op.execute(f"""
        CREATE FUNCTION public.release_approved_grade(wanted_grade uuid)
        RETURNS boolean
        LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $$
            WITH released AS (
                UPDATE public.proposed_grades g
                SET status = 'released', released_at = statement_timestamp()
                FROM public.submissions s
                JOIN public.assignments a ON a.id = s.assignment_id
                JOIN public.enrollments e ON e.course_id = a.course_id
                WHERE g.id = wanted_grade AND g.submission_id = s.id
                  AND g.status = 'approved'
                  AND g.approved_by IS NOT NULL AND g.approved_at IS NOT NULL
                  AND {INSTRUCTOR} AND a.course_id = {COURSE}
                  AND e.user_id = {USER} AND e.role = 'instructor'
                RETURNING 1
            )
            SELECT EXISTS (SELECT 1 FROM released);
        $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION public.release_approved_grade(uuid) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.release_approved_grade(uuid) TO rubrica_release")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    _create_policy_functions()
    _web_policies()
    _ingestion_policies()
    _grading_policies()
    _mcp_policies()
    _release_policies()
    _create_policy(
        "web_snapshots",
        "fetch",
        "INSERT",
        check=f"{GRADING} AND public.fetch_submission_in_run(submission_id)",
    )
    for role in ROLES:
        _create_policy(
            "audit_log",
            role,
            "INSERT",
            check=f"({DELEGATE} OR {GRADING} OR {SYSTEM}) "
            f"AND course_id IS NOT DISTINCT FROM {COURSE}",
        )

    op.execute("""
        CREATE FUNCTION public.reject_audit_mutation()
        RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER audit_log_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_log
        FOR EACH STATEMENT EXECUTE FUNCTION public.reject_audit_mutation()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_log_append_only ON audit_log")
    op.execute("DROP FUNCTION public.reject_audit_mutation()")
    op.execute("DROP FUNCTION public.release_approved_grade(uuid)")
    for table in reversed(TABLES):
        for role in ROLES:
            for operation in ("select", "insert", "update"):
                op.execute(f"DROP POLICY IF EXISTS {role}_{operation} ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION public.blog_chunk_source_matches(text, uuid, uuid, uuid)")
    op.execute("DROP FUNCTION public.fetch_submission_in_run(uuid)")
