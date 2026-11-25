"""Create the initial Rubrica schema and pgvector indexes."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "courses",
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("code", name=op.f("uq_courses_code")),
    )
    op.create_table(
        "jobs",
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_jobs_nonnegative_attempts")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_claim", "jobs", ["kind", "status", "run_after"], unique=False)
    op.create_table(
        "users",
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("totp_secret_enc", sa.LargeBinary(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("role IN ('student', 'instructor')", name=op.f("ck_users_role")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "alerts",
        sa.Column("rule", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"], ["users.id"], name=op.f("fk_alerts_acknowledged_by")
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_alerts_course_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(op.f("ix_alerts_course_id"), "alerts", ["course_id"], unique=False)
    op.create_table(
        "assignments",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("instructions", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="draft", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'published')", name=op.f("ck_assignments_status")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_assignments_course_id")
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name=op.f("fk_assignments_created_by")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assignments")),
    )
    op.create_index(op.f("ix_assignments_course_id"), "assignments", ["course_id"], unique=False)
    op.create_table(
        "audit_log",
        sa.Column(
            "ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("actor_kind", sa.String(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("on_behalf_of", sa.Uuid(), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("args_redacted", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_id", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("prev_hash", sa.String(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "actor_kind IN ('agent', 'user', 'system')", name=op.f("ck_audit_log_actor_kind")
        ),
        sa.CheckConstraint("decision IN ('allowed', 'denied')", name=op.f("ck_audit_log_decision")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_audit_log_course_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
        sa.UniqueConstraint("hash", name=op.f("uq_audit_log_hash")),
    )
    op.create_index(op.f("ix_audit_log_course_id"), "audit_log", ["course_id"], unique=False)
    op.create_table(
        "blog_chunks",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("origin_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("trust", sa.String(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("embedding", VECTOR(dim=384), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "(origin = 'post' AND trust = 'instructor') OR "
            "(origin = 'comment' AND trust = 'untrusted')",
            name=op.f("ck_blog_chunks_origin_trust"),
        ),
        sa.CheckConstraint("origin IN ('post', 'comment')", name=op.f("ck_blog_chunks_origin")),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name=op.f("fk_blog_chunks_author_id")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_blog_chunks_course_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blog_chunks")),
    )
    op.create_index(op.f("ix_blog_chunks_course_id"), "blog_chunks", ["course_id"], unique=False)
    op.create_index(
        "ix_blog_chunks_embedding_cosine",
        "blog_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_table(
        "blog_posts",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name=op.f("fk_blog_posts_author_id")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_blog_posts_course_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blog_posts")),
    )
    op.create_index(op.f("ix_blog_posts_course_id"), "blog_posts", ["course_id"], unique=False)
    op.create_table(
        "chat_transcripts",
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_chat_transcripts_course_id")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], name=op.f("fk_chat_transcripts_student_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_transcripts")),
    )
    op.create_index(
        op.f("ix_chat_transcripts_course_id"), "chat_transcripts", ["course_id"], unique=False
    )
    op.create_table(
        "course_controls",
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("agents_paused", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("paused_by", sa.Uuid(), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_course_controls_course_id")
        ),
        sa.ForeignKeyConstraint(
            ["paused_by"], ["users.id"], name=op.f("fk_course_controls_paused_by")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_controls")),
        sa.UniqueConstraint(
            "course_id",
            name=op.f("uq_course_controls_course_id"),
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_table(
        "drafts",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_agent", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "kind IN ('assignment', 'answer_key', 'rubric')", name=op.f("ck_drafts_kind")
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_drafts_course_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_drafts")),
    )
    op.create_index(op.f("ix_drafts_course_id"), "drafts", ["course_id"], unique=False)
    op.create_table(
        "enrollments",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.CheckConstraint("role IN ('student', 'instructor')", name=op.f("ck_enrollments_role")),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_enrollments_course_id")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_enrollments_user_id")),
        sa.PrimaryKeyConstraint("course_id", "user_id", name=op.f("pk_enrollments")),
    )
    op.create_table(
        "materials",
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_kind", sa.String(), nullable=False),
        sa.Column("uploader_id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "source_kind IN ('instructor', 'third_party')", name=op.f("ck_materials_source_kind")
        ),
        sa.CheckConstraint("status IN ('pending', 'published')", name=op.f("ck_materials_status")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_materials_course_id")),
        sa.ForeignKeyConstraint(
            ["uploader_id"], ["users.id"], name=op.f("fk_materials_uploader_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_materials")),
        sa.UniqueConstraint("id", "course_id", name=op.f("uq_materials_id")),
    )
    op.create_index(op.f("ix_materials_course_id"), "materials", ["course_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("reauth_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_sessions_user_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)
    op.create_table(
        "blog_comments",
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_blog_comments_author_id")
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["blog_posts.id"], name=op.f("fk_blog_comments_post_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_blog_comments")),
    )
    op.create_index(op.f("ix_blog_comments_post_id"), "blog_comments", ["post_id"], unique=False)
    op.create_table(
        "grading_runs",
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("started_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["assignments.id"], name=op.f("fk_grading_runs_assignment_id")
        ),
        sa.ForeignKeyConstraint(
            ["started_by"], ["users.id"], name=op.f("fk_grading_runs_started_by")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grading_runs")),
    )
    op.create_index(
        op.f("ix_grading_runs_assignment_id"), "grading_runs", ["assignment_id"], unique=False
    )
    op.create_table(
        "material_chunks",
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("visibility", sa.String(), server_default="pending", nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.Column("embedding", VECTOR(dim=384), nullable=False),
        sa.Column("source_label", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "visibility IN ('pending', 'published')", name=op.f("ck_material_chunks_visibility")
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_material_chunks_course_id")
        ),
        sa.ForeignKeyConstraint(
            ["material_id", "course_id"],
            ["materials.id", "materials.course_id"],
            name=op.f("fk_material_chunks_material_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_material_chunks")),
    )
    op.create_index(
        op.f("ix_material_chunks_course_id"), "material_chunks", ["course_id"], unique=False
    )
    op.create_index(
        "ix_material_chunks_embedding_cosine",
        "material_chunks",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        op.f("ix_material_chunks_material_id"), "material_chunks", ["material_id"], unique=False
    )
    op.create_table(
        "rubric_criteria",
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("max_points", sa.Numeric(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("kind IN ('objective', 'open')", name=op.f("ck_rubric_criteria_kind")),
        sa.CheckConstraint("max_points > 0", name=op.f("ck_rubric_criteria_positive_max_points")),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["assignments.id"], name=op.f("fk_rubric_criteria_assignment_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rubric_criteria")),
        sa.UniqueConstraint("assignment_id", "id", name="uq_rubric_criteria_assignment_id_id"),
        sa.UniqueConstraint("assignment_id", "position", name="uq_rubric_criteria_position"),
    )
    op.create_table(
        "submissions",
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("body_text", sa.String(), nullable=True),
        sa.Column(
            "objective_answers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("file_ref", sa.String(), nullable=True),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("extracted_text", sa.String(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["assignments.id"], name=op.f("fk_submissions_assignment_id")
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"], name=op.f("fk_submissions_student_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submissions")),
        sa.UniqueConstraint(
            "assignment_id", "student_id", name=op.f("uq_submissions_assignment_id")
        ),
        sa.UniqueConstraint("id", "student_id", name=op.f("uq_submissions_id")),
    )
    op.create_index(op.f("ix_submissions_student_id"), "submissions", ["student_id"], unique=False)
    op.create_table(
        "answer_keys",
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("expected", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(), server_default="draft", nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("status IN ('draft', 'approved')", name=op.f("ck_answer_keys_status")),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], name=op.f("fk_answer_keys_approved_by")
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id", "criterion_id"],
            ["rubric_criteria.assignment_id", "rubric_criteria.id"],
            name=op.f("fk_answer_keys_assignment_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answer_keys")),
        sa.UniqueConstraint(
            "assignment_id", "criterion_id", "version", name=op.f("uq_answer_keys_assignment_id")
        ),
    )
    op.create_table(
        "appeals",
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("reason_text", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="open", nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('open', 'proposed', 'decided')", name=op.f("ck_appeals_status")
        ),
        sa.ForeignKeyConstraint(
            ["submission_id", "student_id"],
            ["submissions.id", "submissions.student_id"],
            name=op.f("fk_appeals_submission_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appeals")),
        sa.UniqueConstraint("id", "submission_id", name=op.f("uq_appeals_id")),
    )
    op.create_index(op.f("ix_appeals_submission_id"), "appeals", ["submission_id"], unique=False)
    op.create_table(
        "capability_tokens",
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("assignment_id", sa.Uuid(), nullable=True),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("audience", sa.String(), server_default="mcp-server", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "(kind = 'grading_run' AND subject_id IS NULL AND run_id IS NOT NULL "
            "AND assignment_id IS NOT NULL) OR "
            "(kind IN ('student_delegate', 'instructor_delegate') AND subject_id IS NOT NULL "
            "AND run_id IS NULL AND assignment_id IS NULL)",
            name=op.f("ck_capability_tokens_kind_context"),
        ),
        sa.CheckConstraint("audience = 'mcp-server'", name=op.f("ck_capability_tokens_audience")),
        sa.ForeignKeyConstraint(
            ["assignment_id"], ["assignments.id"], name=op.f("fk_capability_tokens_assignment_id")
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], name=op.f("fk_capability_tokens_course_id")
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["grading_runs.id"], name=op.f("fk_capability_tokens_run_id")
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"], ["users.id"], name=op.f("fk_capability_tokens_subject_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capability_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_capability_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_capability_tokens_course_id"), "capability_tokens", ["course_id"], unique=False
    )
    op.create_table(
        "grading_results",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total", sa.Numeric(), nullable=True),
        sa.Column("feedback", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("quotes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("validator_status", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("attempt IN (1, 2)", name=op.f("ck_grading_results_attempt")),
        sa.ForeignKeyConstraint(
            ["run_id"], ["grading_runs.id"], name=op.f("fk_grading_results_run_id")
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], name=op.f("fk_grading_results_submission_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grading_results")),
        sa.UniqueConstraint(
            "run_id", "submission_id", "attempt", name=op.f("uq_grading_results_run_id")
        ),
    )
    op.create_index(
        op.f("ix_grading_results_submission_id"), "grading_results", ["submission_id"], unique=False
    )
    op.create_table(
        "manual_queue",
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"], ["users.id"], name=op.f("fk_manual_queue_resolved_by")
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], name=op.f("fk_manual_queue_submission_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_manual_queue")),
    )
    op.create_index(
        op.f("ix_manual_queue_submission_id"), "manual_queue", ["submission_id"], unique=False
    )
    op.create_table(
        "orchestrator_transcripts",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False),
        sa.Column("messages", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["grading_runs.id"], name=op.f("fk_orchestrator_transcripts_run_id")
        ),
        sa.PrimaryKeyConstraint("run_id", "step", name=op.f("pk_orchestrator_transcripts")),
    )
    op.create_table(
        "proposed_grades",
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("result_ids", postgresql.ARRAY(postgresql.UUID()), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column(
            "flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'released', 'rejected')",
            name=op.f("ck_proposed_grades_status"),
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], name=op.f("fk_proposed_grades_approved_by")
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], name=op.f("fk_proposed_grades_submission_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_proposed_grades")),
    )
    op.create_index(
        op.f("ix_proposed_grades_submission_id"), "proposed_grades", ["submission_id"], unique=False
    )
    op.create_table(
        "web_snapshots",
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("final_url", sa.String(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sha256", sa.String(), nullable=True),
        sa.Column("text", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], name=op.f("fk_web_snapshots_submission_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_web_snapshots")),
    )
    op.create_index(
        op.f("ix_web_snapshots_submission_id"), "web_snapshots", ["submission_id"], unique=False
    )
    op.create_table(
        "citation_verdicts",
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("result_id", sa.Uuid(), nullable=False),
        sa.Column("claim", sa.String(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "verdict IN ('supports', 'does_not_support', 'unrelated', 'unreadable')",
            name=op.f("ck_citation_verdicts_verdict"),
        ),
        sa.ForeignKeyConstraint(
            ["result_id"], ["grading_results.id"], name=op.f("fk_citation_verdicts_result_id")
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["web_snapshots.id"], name=op.f("fk_citation_verdicts_snapshot_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_citation_verdicts")),
    )
    op.create_index(
        op.f("ix_citation_verdicts_result_id"), "citation_verdicts", ["result_id"], unique=False
    )
    op.create_index(
        op.f("ix_citation_verdicts_snapshot_id"), "citation_verdicts", ["snapshot_id"], unique=False
    )
    op.create_table(
        "grade_change_proposals",
        sa.Column("appeal_id", sa.Uuid(), nullable=False),
        sa.Column("submission_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rationale", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name=op.f("ck_grade_change_proposals_status"),
        ),
        sa.ForeignKeyConstraint(
            ["appeal_id", "submission_id"],
            ["appeals.id", "appeals.submission_id"],
            name=op.f("fk_grade_change_proposals_appeal_id"),
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"], ["users.id"], name=op.f("fk_grade_change_proposals_decided_by")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grade_change_proposals")),
    )
    op.create_index(
        op.f("ix_grade_change_proposals_appeal_id"),
        "grade_change_proposals",
        ["appeal_id"],
        unique=False,
    )
    op.execute("INSERT INTO course_controls DEFAULT VALUES")


def downgrade() -> None:
    op.drop_index(op.f("ix_grade_change_proposals_appeal_id"), table_name="grade_change_proposals")
    op.drop_table("grade_change_proposals")
    op.drop_index(op.f("ix_citation_verdicts_snapshot_id"), table_name="citation_verdicts")
    op.drop_index(op.f("ix_citation_verdicts_result_id"), table_name="citation_verdicts")
    op.drop_table("citation_verdicts")
    op.drop_index(op.f("ix_web_snapshots_submission_id"), table_name="web_snapshots")
    op.drop_table("web_snapshots")
    op.drop_index(op.f("ix_proposed_grades_submission_id"), table_name="proposed_grades")
    op.drop_table("proposed_grades")
    op.drop_table("orchestrator_transcripts")
    op.drop_index(op.f("ix_manual_queue_submission_id"), table_name="manual_queue")
    op.drop_table("manual_queue")
    op.drop_index(op.f("ix_grading_results_submission_id"), table_name="grading_results")
    op.drop_table("grading_results")
    op.drop_index(op.f("ix_capability_tokens_course_id"), table_name="capability_tokens")
    op.drop_table("capability_tokens")
    op.drop_index(op.f("ix_appeals_submission_id"), table_name="appeals")
    op.drop_table("appeals")
    op.drop_table("answer_keys")
    op.drop_index(op.f("ix_submissions_student_id"), table_name="submissions")
    op.drop_table("submissions")
    op.drop_table("rubric_criteria")
    op.drop_index(op.f("ix_material_chunks_material_id"), table_name="material_chunks")
    op.drop_index(
        "ix_material_chunks_embedding_cosine",
        table_name="material_chunks",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index(op.f("ix_material_chunks_course_id"), table_name="material_chunks")
    op.drop_table("material_chunks")
    op.drop_index(op.f("ix_grading_runs_assignment_id"), table_name="grading_runs")
    op.drop_table("grading_runs")
    op.drop_index(op.f("ix_blog_comments_post_id"), table_name="blog_comments")
    op.drop_table("blog_comments")
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_materials_course_id"), table_name="materials")
    op.drop_table("materials")
    op.drop_table("enrollments")
    op.drop_index(op.f("ix_drafts_course_id"), table_name="drafts")
    op.drop_table("drafts")
    op.drop_table("course_controls")
    op.drop_index(op.f("ix_chat_transcripts_course_id"), table_name="chat_transcripts")
    op.drop_table("chat_transcripts")
    op.drop_index(op.f("ix_blog_posts_course_id"), table_name="blog_posts")
    op.drop_table("blog_posts")
    op.drop_index(
        "ix_blog_chunks_embedding_cosine",
        table_name="blog_chunks",
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.drop_index(op.f("ix_blog_chunks_course_id"), table_name="blog_chunks")
    op.drop_table("blog_chunks")
    op.drop_index(op.f("ix_audit_log_course_id"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_assignments_course_id"), table_name="assignments")
    op.drop_table("assignments")
    op.drop_index(op.f("ix_alerts_course_id"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_table("users")
    op.drop_index("ix_jobs_claim", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("courses")
