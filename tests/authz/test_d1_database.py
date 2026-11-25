"""Run against a disposable loopback PostgreSQL 18/pgvector cluster.

Set RUBRICA_D1_TEST_PORT to its published port. The rubrica database must be empty
and allow the test owner and fixture roles to connect (e.g. a local trust cluster).
"""

import os
from datetime import UTC, datetime
from hashlib import sha256
from importlib import import_module
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import URL, create_engine, func, insert, inspect, select, text, update
from sqlalchemy.exc import DBAPIError

from backend.db import SessionContext, session
from backend.db.migrate import migration_config
from backend.db.models import (
    AnswerKey,
    Assignment,
    AuditEvent,
    BlogChunk,
    BlogPost,
    Course,
    Enrollment,
    GradingResult,
    GradingRun,
    Job,
    Material,
    MaterialChunk,
    ProposedGrade,
    RubricCriterion,
    Submission,
    User,
    WebSnapshot,
)
from backend.ingestion.index_material import index_material
from backend.ingestion.worker import claim_job, finish_job
from backend.retrieval.search import search_for_agent, search_for_grading

KEYMARK = "KEYMARK-a4f7"
NOW = datetime(2026, 11, 25, tzinfo=UTC)


def _seed(conn):
    def add(model, **values):
        key = uuid4()
        conn.execute(insert(model.__table__).inline().values(id=key, **values))
        return key

    def user(name, role):
        return add(
            User, email=f"{name}@example.edu", display_name=name, role=role, password_hash="!"
        )

    courses = [add(Course, code=f"C{i}", title=f"Course {i}") for i in range(2)]
    instructor = user("instructor", "instructor")
    students = [user(f"student{i}", "student") for i in range(2)]
    conn.execute(
        insert(Enrollment),
        [
            {"course_id": courses[0], "user_id": instructor, "role": "instructor"},
            *[
                {"course_id": courses[0], "user_id": student, "role": "student"}
                for student in students
            ],
        ],
    )
    assignments = [
        add(
            Assignment,
            course_id=course,
            title="Assignment",
            instructions="",
            due_at=NOW,
            status="published",
            created_by=instructor,
        )
        for course in [courses[0], *courses]
    ]
    criterion = add(
        RubricCriterion,
        assignment_id=assignments[0],
        label="Open",
        max_points=1,
        kind="open",
        position=0,
    )
    answer_key = add(
        AnswerKey,
        assignment_id=assignments[0],
        criterion_id=criterion,
        content=KEYMARK,
        status="approved",
        approved_by=instructor,
    )
    submissions = [
        add(
            Submission,
            assignment_id=assignment,
            student_id=student,
            body_text="Synthetic",
            sha256="test",
        )
        for assignment, student in zip(
            [assignments[0], assignments[0], assignments[1]],
            [*students, students[0]],
            strict=True,
        )
    ]
    run = add(GradingRun, assignment_id=assignments[0], started_by=instructor, status="running")
    results = [
        add(
            GradingResult,
            run_id=run,
            submission_id=submission,
            attempt=attempt,
            model_id="fake",
            prompt_version="test",
            validator_status="accepted",
        )
        for submission, attempt in [(submissions[0], 1), (submissions[0], 2), (submissions[1], 1)]
    ]
    released = add(
        ProposedGrade,
        submission_id=submissions[0],
        result_ids=results[:1],
        status="released",
        approved_by=instructor,
        approved_at=NOW,
        released_at=NOW,
    )
    pending = add(ProposedGrade, submission_id=submissions[1], result_ids=results[2:])
    embedding = [1.0, *([0.0] * 383)]
    for course, status, label in [
        (courses[0], "published", "Published"),
        (courses[0], "pending", "Pending"),
        (courses[1], "published", "Other course"),
    ]:
        material = add(
            Material,
            course_id=course,
            source_kind="instructor",
            title=label,
            uploader_id=instructor,
            status=status,
            sha256="test",
        )
        add(
            MaterialChunk,
            material_id=material,
            course_id=course,
            visibility=status,
            text=label,
            source_label=label,
            embedding=embedding,
        )
    for course, label in zip(courses, ["Course blog", "Other blog"], strict=True):
        post = add(
            BlogPost,
            course_id=course,
            author_id=instructor,
            body=label,
            sha256="test",
        )
        add(
            BlogChunk,
            course_id=course,
            origin="post",
            origin_id=post,
            author_id=instructor,
            trust="instructor",
            text=label,
            embedding=embedding,
        )

    return {
        "embedding": embedding,
        "courses": courses,
        "instructor": instructor,
        "students": students,
        "assignments": assignments,
        "answer_key": answer_key,
        "submissions": submissions,
        "run": run,
        "results": results,
        "released": released,
        "pending": pending,
    }


@pytest.fixture(scope="module")
def database():
    port = os.environ.get("RUBRICA_D1_TEST_PORT")
    if not port:
        pytest.skip("requires a disposable PostgreSQL 18/pgvector cluster")

    owner_url = URL.create(
        "postgresql+psycopg",
        username="rubrica_owner",
        host="127.0.0.1",
        port=int(port),
        database="rubrica",
    )
    owner = create_engine(owner_url, hide_parameters=True)
    module = import_module("backend.db.session")
    engines = {}

    def engine(role):
        if role not in engines:
            engines[role] = create_engine(
                owner_url.set(username=role),
                hide_parameters=True,
                pool_size=1,
                max_overflow=0,
            )
        return engines[role]

    config = migration_config()
    upgraded = False
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(module, "_read_password", lambda _: "CANARY-T19-a943")
            patch.setattr(module, "_runtime_engine", engine)
            with owner.connect() as conn:
                tables = set(inspect(conn).get_table_names())
                assert tables <= {"alembic_version"}, "D1 tests require an empty database"
                if "alembic_version" in tables:
                    assert not conn.scalar(text("SELECT count(*) FROM alembic_version"))
                conn.rollback()
                config.attributes["connection"] = conn
                command.upgrade(config, "head")
                upgraded = True
                command.upgrade(config, "head")
                command.check(config)
            with owner.begin() as conn:
                rows = _seed(conn)
            yield rows, engine, owner
    finally:
        for runtime in engines.values():
            runtime.dispose()
        if upgraded:
            with owner.connect() as conn:
                config.attributes["connection"] = conn
                command.downgrade(config, "base")
        owner.dispose()


def test_mcp_student_sees_only_released_own_feedback_and_published_sources(database, monkeypatch):
    rows, engine, _ = database
    monkeypatch.setenv("DB_ROLE", "rubrica_mcp")
    student = SessionContext("student", rows["students"][0], rows["courses"][0])
    with session("rubrica_mcp", student) as db:
        assert db.scalars(select(ProposedGrade.id)).all() == [rows["released"]]
        assert db.scalars(select(GradingResult.id)).all() == rows["results"][:1]
        assert db.scalars(select(AnswerKey.id)).all() == []
        assert db.scalars(select(MaterialChunk.text)).all() == ["Published"]
        assert db.scalars(select(BlogChunk.text)).all() == ["Course blog"]

    # Check the same pooled connection after the transaction ends.
    with engine("rubrica_mcp").connect() as conn:
        assert conn.scalars(select(Assignment.id)).all() == []


def test_instructor_key_is_separate_from_retrieval_chunks(database, monkeypatch):
    rows, _, owner = database
    monkeypatch.setenv("DB_ROLE", "rubrica_mcp")
    instructor = SessionContext("instructor", rows["instructor"], rows["courses"][0])
    with session("rubrica_mcp", instructor) as db:
        assert db.get(AnswerKey, rows["answer_key"]).content == KEYMARK

    with owner.connect() as conn:
        for chunk in (MaterialChunk, BlogChunk):
            assert (
                conn.scalar(
                    select(func.count()).select_from(chunk).where(chunk.text.contains("KEYMARK"))
                )
                == 0
            )


def test_grading_run_is_scoped_to_its_assignment(database, monkeypatch):
    rows, _, _ = database
    monkeypatch.setenv("DB_ROLE", "rubrica_grading")
    run = SessionContext("grading_run", course_id=rows["courses"][0], run_id=rows["run"])
    with session("rubrica_grading", run) as db:
        assert db.scalars(select(Assignment.id)).all() == rows["assignments"][:1]
        assert set(db.scalars(select(Submission.id))) == set(rows["submissions"][:2])
        assert db.scalars(select(AnswerKey.id)).all() == [rows["answer_key"]]
        assert db.scalars(select(MaterialChunk.text)).all() == ["Published"]
    with pytest.raises(DBAPIError) as error, session("rubrica_grading", run) as db:
        db.execute(select(BlogChunk.id))
    assert error.value.orig.sqlstate == "42501"


def test_only_release_role_can_publish_an_approved_grade(database, monkeypatch):
    rows, _, _ = database
    instructor = SessionContext("instructor", rows["instructor"], rows["courses"][0])
    wrong_course = SessionContext("instructor", rows["instructor"], rows["courses"][1])
    select_ids = select(ProposedGrade.id)
    update_grade = (
        update(ProposedGrade.__table__).where(ProposedGrade.id == rows["pending"]).inline()
    )
    monkeypatch.setenv("DB_ROLE", "rubrica_web")
    with session("rubrica_web", wrong_course) as db:
        assert db.scalars(select(Assignment.id)).all() == []
    with pytest.raises(DBAPIError) as error, session("rubrica_web", instructor) as db:
        db.execute(update_grade.values(status="released"))
    assert error.value.orig.sqlstate == "42501"
    with session("rubrica_web", instructor) as db:
        updated = db.execute(
            update_grade.values(status="approved", approved_by=rows["instructor"], approved_at=NOW)
        )
        assert updated.rowcount == 1

    monkeypatch.setenv("DB_ROLE", "rubrica_mcp")
    with pytest.raises(DBAPIError) as error, session("rubrica_mcp", instructor) as db:
        db.execute(update_grade.values(status="released"))
    assert error.value.orig.sqlstate == "42501"

    monkeypatch.setenv("DB_ROLE", "rubrica_release")
    release = text("SELECT public.release_approved_grade(:grade)")
    with session("rubrica_release", wrong_course) as db:
        assert not db.scalar(release, {"grade": rows["pending"]})
    with session("rubrica_release", instructor) as db:
        assert db.scalars(select_ids.where(ProposedGrade.status == "approved")).all() == [
            rows["pending"]
        ]
        assert db.scalar(release, {"grade": rows["pending"]})
        assert db.scalars(select_ids).all() == []
        assert not db.scalar(release, {"grade": rows["pending"]})

    monkeypatch.setenv("DB_ROLE", "rubrica_mcp")
    student = SessionContext("student", rows["students"][1], rows["courses"][0])
    with session("rubrica_mcp", student) as db:
        assert db.scalars(select_ids).all() == [rows["pending"]]


def test_audit_trigger_and_runtime_grants_are_append_only(database, monkeypatch):
    rows, _, owner = database
    monkeypatch.setenv("DB_ROLE", "rubrica_mcp")
    course = rows["courses"][0]
    student = SessionContext("student", rows["students"][0], course)
    with session("rubrica_mcp", student) as db:
        db.execute(
            insert(AuditEvent.__table__)
            .inline()
            .values(
                actor_kind="agent",
                actor_id="chat-agent",
                course_id=course,
                action="test",
                args_redacted={},
                decision="allowed",
                result_summary={},
                prev_hash="0",
                hash="test",
            )
        )
        assert not db.scalar(
            text(
                "SELECT has_table_privilege(current_user, 'audit_log', 'UPDATE, DELETE, TRUNCATE')"
            )
        )
    with pytest.raises(DBAPIError, match="audit_log is append-only"), owner.begin() as conn:
        conn.execute(update(AuditEvent.__table__).values(action="changed"))


def test_ingestion_cannot_publish_pending_material_or_read_keys(database, monkeypatch):
    rows, _, _ = database
    monkeypatch.setenv("DB_ROLE", "rubrica_ingest")
    course = rows["courses"][0]
    job = SessionContext("system", course_id=course)
    with session("rubrica_ingest", job) as db:
        pending = db.scalar(select(Material.id).where(Material.status == "pending"))
        assert pending is not None
    chunk = (
        insert(MaterialChunk.__table__)
        .inline()
        .values(
            material_id=pending,
            course_id=course,
            text="Synthetic",
            source_label="Test",
            embedding=rows["embedding"],
        )
    )
    with pytest.raises(DBAPIError) as error, session("rubrica_ingest", job) as db:
        db.execute(chunk.values(visibility="published"))
    assert error.value.orig.sqlstate == "42501"
    with pytest.raises(DBAPIError) as error, session("rubrica_ingest", job) as db:
        db.execute(select(AnswerKey.id))
    assert error.value.orig.sqlstate == "42501"


def test_fetch_can_write_only_for_submissions_in_its_run(database, monkeypatch):
    rows, _, _ = database
    monkeypatch.setenv("DB_ROLE", "rubrica_fetch")
    run = SessionContext("grading_run", course_id=rows["courses"][0], run_id=rows["run"])
    snapshot = (
        insert(WebSnapshot.__table__)
        .inline()
        .values(
            url="https://example.edu/",
            status="blocked",
        )
    )
    with pytest.raises(DBAPIError) as error, session("rubrica_fetch", run) as db:
        db.execute(snapshot.values(submission_id=rows["submissions"][2]))
    assert error.value.orig.sqlstate == "42501"
    with session("rubrica_fetch", run) as db:
        db.execute(snapshot.values(submission_id=rows["submissions"][0]))
    with pytest.raises(DBAPIError) as error, session("rubrica_fetch", run) as db:
        db.execute(select(WebSnapshot.id))
    assert error.value.orig.sqlstate == "42501"


def test_vector_search_separates_blog_scope_and_grading(database, monkeypatch):
    rows, _, _ = database
    course, other = rows["courses"]

    def embed(_):
        return rows["embedding"]

    monkeypatch.setenv("DB_ROLE", "rubrica_mcp")
    student = SessionContext("student", rows["students"][0], course)
    with session("rubrica_mcp", student) as db:
        hits = search_for_agent(db, "course notes", 8, embed=embed)
        assert {hit.text for hit in hits} == {"Published", "Course blog"}
        assert len(search_for_agent(db, "course notes", 1, embed=embed)) == 1

    monkeypatch.setenv("DB_ROLE", "rubrica_grading")
    run = SessionContext("grading_run", course_id=course, run_id=rows["run"])
    with session("rubrica_grading", run) as db:
        hits = search_for_grading(db, course, "course notes", 8, embed=embed)
        assert [(hit.text, hit.trust) for hit in hits] == [("Published", "instructor")]
        assert search_for_grading(db, other, "course notes", 8, embed=embed) == []


def test_material_index_retry_keeps_one_pending_chunk(database, monkeypatch):
    rows, _, owner = database
    course = rows["courses"][0]
    source = b"Local synthetic source"
    material = uuid4()
    with owner.begin() as conn:
        conn.execute(
            insert(Material.__table__).values(
                id=material,
                course_id=course,
                title="Synthetic retry",
                source_kind="instructor",
                uploader_id=rows["instructor"],
                sha256=sha256(source).hexdigest(),
            )
        )

    def embed(_):
        return rows["embedding"]

    monkeypatch.setenv("DB_ROLE", "rubrica_ingest")
    args = {
        "material_id": material,
        "course_id": course,
        "source": source,
        "result": {"text": source.decode(), "has_text_layer": True},
        "embed": embed,
    }
    assert index_material(**args) == 1
    assert index_material(**args) == 0
    with pytest.raises(ValueError, match="Material source"):
        index_material(**(args | {"source": b"different source"}))
    with owner.connect() as conn:
        assert conn.scalars(
            select(MaterialChunk.visibility).where(MaterialChunk.material_id == material)
        ).all() == ["pending"]


def test_ingestion_lease_excludes_other_services_jobs(database, monkeypatch):
    _, _, owner = database
    parse_job, grading_job = uuid4(), uuid4()
    with owner.begin() as conn:
        for job, kind in ((grading_job, "grading_run"), (parse_job, "parse_material")):
            conn.execute(
                insert(Job.__table__).values(
                    id=job,
                    kind=kind,
                    status="queued",
                    payload={},
                    run_after=NOW,
                )
            )

    monkeypatch.setenv("DB_ROLE", "rubrica_ingest")
    job_id, kind, _, lease = claim_job()
    assert kind == "parse_material"
    assert job_id == parse_job
    assert claim_job() is None
    assert finish_job(parse_job, lease, "done")
    assert not finish_job(parse_job, lease, "failed")
    with owner.connect() as conn:
        assert conn.scalar(select(Job.status).where(Job.id == parse_job)) == "done"
        assert conn.scalar(select(Job.status).where(Job.id == grading_job)) == "queued"


def test_ingestion_stores_submission_text_only_for_matching_course_and_hash(database, monkeypatch):
    rows, _, owner = database
    course, other = rows["courses"]
    submission = rows["submissions"][0]
    statement = text("SELECT public.store_parsed_submission(:id, :digest, :contents)")
    parameters = {"id": submission, "digest": "test", "contents": "Synthetic parsed text"}
    monkeypatch.setenv("DB_ROLE", "rubrica_ingest")
    with session("rubrica_ingest", SessionContext("system", course_id=other)) as db:
        assert not db.scalar(statement, parameters)
    with session("rubrica_ingest", SessionContext("system", course_id=course)) as db:
        assert not db.scalar(statement, parameters | {"digest": "different"})
        assert db.scalar(statement, parameters)
    with owner.connect() as conn:
        extracted = conn.scalar(
            select(Submission.extracted_text).where(Submission.id == submission)
        )
        assert extracted == "Synthetic parsed text"
