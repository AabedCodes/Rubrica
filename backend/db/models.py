"""PostgreSQL models for the shared database contract."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
        }
    )
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        dict: JSONB,
        list: JSONB,
    }


class Identified:
    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())


class Created:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class User(Identified, Created, Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('student', 'instructor')", name="role"),)

    email: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str]
    role: Mapped[str]
    password_hash: Mapped[str]
    totp_secret_enc: Mapped[bytes | None]


class Course(Identified, Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (CheckConstraint("role IN ('student', 'instructor')", name="role"),)

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    role: Mapped[str]


class Assignment(Identified, Base):
    __tablename__ = "assignments"
    __table_args__ = (CheckConstraint("status IN ('draft', 'published')", name="status"),)

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str]
    instructions: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="draft")
    due_at: Mapped[datetime]
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(server_default="1")


class RubricCriterion(Identified, Base):
    __tablename__ = "rubric_criteria"
    __table_args__ = (
        CheckConstraint("max_points > 0", name="positive_max_points"),
        CheckConstraint("kind IN ('objective', 'open')", name="kind"),
        UniqueConstraint("assignment_id", "id", name="uq_rubric_criteria_assignment_id_id"),
        UniqueConstraint("assignment_id", "position", name="uq_rubric_criteria_position"),
    )

    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignments.id"))
    label: Mapped[str]
    max_points: Mapped[Decimal]
    kind: Mapped[str]
    position: Mapped[int]


class AnswerKey(Identified, Base):
    __tablename__ = "answer_keys"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved')", name="status"),
        ForeignKeyConstraint(
            ["assignment_id", "criterion_id"],
            ["rubric_criteria.assignment_id", "rubric_criteria.id"],
        ),
        UniqueConstraint("assignment_id", "criterion_id", "version"),
    )

    assignment_id: Mapped[UUID]
    criterion_id: Mapped[UUID]
    content: Mapped[str]
    expected: Mapped[dict | None]
    status: Mapped[str] = mapped_column(server_default="draft")
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    version: Mapped[int] = mapped_column(server_default="1")


class Material(Identified, Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint("source_kind IN ('instructor', 'third_party')", name="source_kind"),
        CheckConstraint("status IN ('pending', 'published')", name="status"),
        UniqueConstraint("id", "course_id"),
    )

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    title: Mapped[str]
    source_kind: Mapped[str]
    uploader_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    sha256: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="pending")
    version: Mapped[int] = mapped_column(server_default="1")


class MaterialChunk(Identified, Base):
    __tablename__ = "material_chunks"
    __table_args__ = (
        CheckConstraint("visibility IN ('pending', 'published')", name="visibility"),
        ForeignKeyConstraint(["material_id", "course_id"], ["materials.id", "materials.course_id"]),
        Index(
            "ix_material_chunks_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    material_id: Mapped[UUID] = mapped_column(index=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    visibility: Mapped[str] = mapped_column(server_default="pending")
    text: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384))
    source_label: Mapped[str]


class BlogPost(Identified, Created, Base):
    __tablename__ = "blog_posts"

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str]
    sha256: Mapped[str]


class BlogComment(Identified, Created, Base):
    __tablename__ = "blog_comments"

    post_id: Mapped[UUID] = mapped_column(ForeignKey("blog_posts.id"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str]
    sha256: Mapped[str]


class BlogChunk(Identified, Base):
    __tablename__ = "blog_chunks"
    __table_args__ = (
        CheckConstraint("origin IN ('post', 'comment')", name="origin"),
        CheckConstraint(
            "(origin = 'post' AND trust = 'instructor') OR "
            "(origin = 'comment' AND trust = 'untrusted')",
            name="origin_trust",
        ),
        Index(
            "ix_blog_chunks_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    origin: Mapped[str]
    origin_id: Mapped[UUID]
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    trust: Mapped[str]
    text: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(VECTOR(384))


class Submission(Identified, Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id"),
        UniqueConstraint("id", "student_id"),
    )

    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignments.id"))
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    body_text: Mapped[str | None]
    objective_answers: Mapped[dict] = mapped_column(server_default=text("'{}'::jsonb"))
    file_ref: Mapped[str | None]
    sha256: Mapped[str]
    extracted_text: Mapped[str | None]
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now())


class GradingRun(Identified, Base):
    __tablename__ = "grading_runs"

    assignment_id: Mapped[UUID] = mapped_column(ForeignKey("assignments.id"), index=True)
    started_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str]
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ended_at: Mapped[datetime | None]


class GradingResult(Identified, Created, Base):
    __tablename__ = "grading_results"
    __table_args__ = (
        CheckConstraint("attempt IN (1, 2)", name="attempt"),
        UniqueConstraint("run_id", "submission_id", "attempt"),
    )

    run_id: Mapped[UUID] = mapped_column(ForeignKey("grading_runs.id"))
    submission_id: Mapped[UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    attempt: Mapped[int]
    scores: Mapped[dict | None]
    total: Mapped[Decimal | None]
    feedback: Mapped[dict | None]
    quotes: Mapped[dict | None]
    model_id: Mapped[str]
    prompt_version: Mapped[str]
    validator_status: Mapped[str]


class ProposedGrade(Identified, Base):
    __tablename__ = "proposed_grades"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'released', 'rejected')", name="status"),
    )

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    result_ids: Mapped[list[UUID]] = mapped_column(ARRAY(PG_UUID()))
    status: Mapped[str] = mapped_column(server_default="pending")
    flags: Mapped[dict] = mapped_column(server_default=text("'{}'::jsonb"))
    approved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    released_at: Mapped[datetime | None]


class WebSnapshot(Identified, Base):
    __tablename__ = "web_snapshots"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    url: Mapped[str]
    final_url: Mapped[str | None]
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    sha256: Mapped[str | None]
    text: Mapped[str | None]
    status: Mapped[str]


class CitationVerdict(Identified, Base):
    __tablename__ = "citation_verdicts"
    __table_args__ = (
        CheckConstraint(
            "verdict IN ('supports', 'does_not_support', 'unrelated', 'unreadable')",
            name="verdict",
        ),
    )

    snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("web_snapshots.id"), index=True)
    result_id: Mapped[UUID] = mapped_column(ForeignKey("grading_results.id"), index=True)
    claim: Mapped[str]
    verdict: Mapped[str]


class Appeal(Identified, Created, Base):
    __tablename__ = "appeals"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'proposed', 'decided')", name="status"),
        ForeignKeyConstraint(
            ["submission_id", "student_id"], ["submissions.id", "submissions.student_id"]
        ),
        UniqueConstraint("id", "submission_id"),
    )

    submission_id: Mapped[UUID] = mapped_column(index=True)
    student_id: Mapped[UUID]
    reason_text: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="open")


class GradeChangeProposal(Identified, Base):
    __tablename__ = "grade_change_proposals"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'accepted', 'rejected')", name="status"),
        ForeignKeyConstraint(
            ["appeal_id", "submission_id"], ["appeals.id", "appeals.submission_id"]
        ),
    )

    appeal_id: Mapped[UUID] = mapped_column(index=True)
    submission_id: Mapped[UUID]
    proposed_scores: Mapped[dict]
    rationale: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="pending")
    decided_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None]


class Draft(Identified, Base):
    __tablename__ = "drafts"
    __table_args__ = (
        CheckConstraint("kind IN ('assignment', 'answer_key', 'rubric')", name="kind"),
    )

    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    kind: Mapped[str]
    payload: Mapped[dict]
    created_by_agent: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="pending")


class ManualQueueItem(Identified, Created, Base):
    __tablename__ = "manual_queue"

    submission_id: Mapped[UUID] = mapped_column(ForeignKey("submissions.id"), index=True)
    reason_code: Mapped[str]
    resolved_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]


class ChatTranscript(Identified, Created, Base):
    __tablename__ = "chat_transcripts"

    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    messages: Mapped[list]


class OrchestratorTranscript(Created, Base):
    __tablename__ = "orchestrator_transcripts"

    run_id: Mapped[UUID] = mapped_column(ForeignKey("grading_runs.id"), primary_key=True)
    step: Mapped[int] = mapped_column(primary_key=True)
    messages: Mapped[list]


class AuditEvent(Identified, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        CheckConstraint("actor_kind IN ('agent', 'user', 'system')", name="actor_kind"),
        CheckConstraint("decision IN ('allowed', 'denied')", name="decision"),
    )

    ts: Mapped[datetime] = mapped_column(server_default=func.now())
    actor_kind: Mapped[str]
    actor_id: Mapped[str]
    on_behalf_of: Mapped[UUID | None]
    course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id"), index=True)
    action: Mapped[str]
    args_redacted: Mapped[dict]
    decision: Mapped[str]
    reason_code: Mapped[str | None]
    result_summary: Mapped[dict]
    model_id: Mapped[str | None]
    prompt_version: Mapped[str | None]
    prev_hash: Mapped[str]
    hash: Mapped[str] = mapped_column(unique=True)


class UserSession(Identified, Created, Base):
    __tablename__ = "sessions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reauth_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]


class CapabilityToken(Identified, Base):
    __tablename__ = "capability_tokens"
    __table_args__ = (
        CheckConstraint("audience = 'mcp-server'", name="audience"),
        CheckConstraint(
            "(kind = 'grading_run' AND subject_id IS NULL AND run_id IS NOT NULL "
            "AND assignment_id IS NOT NULL) OR "
            "(kind IN ('student_delegate', 'instructor_delegate') AND subject_id IS NOT NULL "
            "AND run_id IS NULL AND assignment_id IS NULL)",
            name="kind_context",
        ),
    )

    token_hash: Mapped[str] = mapped_column(unique=True)
    kind: Mapped[str]
    subject_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("grading_runs.id"))
    assignment_id: Mapped[UUID | None] = mapped_column(ForeignKey("assignments.id"))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text()))
    audience: Mapped[str] = mapped_column(server_default="mcp-server")
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]


class Alert(Identified, Created, Base):
    __tablename__ = "alerts"

    rule: Mapped[str]
    severity: Mapped[str]
    course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id"), index=True)
    details: Mapped[dict]
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))


class CourseControl(Identified, Base):
    __tablename__ = "course_controls"
    __table_args__ = (UniqueConstraint("course_id", postgresql_nulls_not_distinct=True),)

    course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id"))
    agents_paused: Mapped[bool] = mapped_column(server_default=text("false"))
    paused_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    paused_at: Mapped[datetime | None]
    reason: Mapped[str | None]


class Job(Identified, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="nonnegative_attempts"),
        Index("ix_jobs_claim", "kind", "status", "run_after"),
    )

    kind: Mapped[str]
    payload: Mapped[dict]
    status: Mapped[str]
    attempts: Mapped[int] = mapped_column(server_default="0")
    run_after: Mapped[datetime] = mapped_column(server_default=func.now())
    locked_at: Mapped[datetime | None]
