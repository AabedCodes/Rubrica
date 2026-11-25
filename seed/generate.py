"""Load deterministic, synthetic course data for local Rubrica development."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from os import environ
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from argon2 import PasswordHasher
from faker import Faker
from sqlalchemy import Connection, func, update
from sqlalchemy.dialects.postgresql import insert

from backend.db import models as db
from backend.db.session import OWNER_ROLE, _create_engine

FIXTURE_ROOT = Path(__file__).parent
CREATED = datetime(2026, 11, 23, 9, tzinfo=UTC)
DUE = datetime(2026, 12, 1, 21, tzinfo=UTC)
DEMO_PASSWORD = "CANARY-T19-d200-local-demo"  # noqa: S105 (synthetic demo fixture)
HASHER = PasswordHasher()


def fixture_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"https://rubrica.example.edu/seed/v1/{name}")


def digest(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _add(conn: Connection, table, **values) -> None:
    conn.execute(
        insert(table)
        .values(**values)
        .on_conflict_do_nothing(
            index_elements=list(table.primary_key.columns),
        )
    )


def _user(conn: Connection, fake: Faker, slug: str, role: str) -> UUID:
    user = fixture_id(slug)
    _add(
        conn,
        db.User.__table__,
        id=user,
        email=f"{slug}@example.edu",
        display_name=fake.name(),
        role=role,
        password_hash=HASHER.hash(DEMO_PASSWORD, salt=user.bytes),
        created_at=CREATED,
    )
    return user


def _assignment(conn: Connection, slug: str, course: UUID, instructor: UUID, title: str) -> UUID:
    assignment = fixture_id(slug)
    _add(
        conn,
        db.Assignment.__table__,
        id=assignment,
        course_id=course,
        title=title,
        instructions="Answer the objective question and justify your explanation.",
        status="published",
        due_at=DUE,
        created_by=instructor,
    )
    for position, label, kind, points in (
        (0, "Choice", "objective", 2),
        (1, "Explanation", "open", 3),
    ):
        criterion = fixture_id(f"{slug}/{kind}")
        _add(
            conn,
            db.RubricCriterion.__table__,
            id=criterion,
            assignment_id=assignment,
            label=label,
            max_points=points,
            kind=kind,
            position=position,
        )
        expected = {"type": "choice", "value": "B"} if kind == "objective" else None
        marker = f"KEYMARK-{criterion.hex[:8]}"
        _add(
            conn,
            db.AnswerKey.__table__,
            id=fixture_id(f"{slug}/{kind}/key"),
            assignment_id=assignment,
            criterion_id=criterion,
            content=f"{marker} · Accept a clear, well-supported answer.",
            expected=expected,
            status="approved",
            approved_by=instructor,
        )
    return assignment


def _seed_course(conn: Connection, fake: Faker, number: int) -> None:
    slug = f"course-{number}"
    course = fixture_id(slug)
    instructor = _user(conn, fake, f"instructor-{number}", "instructor")
    _add(
        conn,
        db.Course.__table__,
        id=course,
        code=f"DEMO{number:02d}",
        title=f"Synthetic Course {number}",
    )
    _add(conn, db.Enrollment.__table__, course_id=course, user_id=instructor, role="instructor")

    first_slug = f"{slug}/assignment-1"
    first = _assignment(conn, first_slug, course, instructor, "Concepts")
    _assignment(conn, f"{slug}/assignment-2", course, instructor, "Application")

    for source, title, kind in (
        ("lecture", "Synthetic lecture notes", "instructor"),
        ("chapter", "Synthetic third-party chapter", "third_party"),
    ):
        content = (FIXTURE_ROOT / "materials" / f"{source}.txt").read_text(encoding="utf-8")
        _add(
            conn,
            db.Material.__table__,
            id=fixture_id(f"{slug}/{source}"),
            course_id=course,
            title=title,
            source_kind=kind,
            uploader_id=instructor,
            sha256=digest(content),
            status="published",
        )

    post = fixture_id(f"{slug}/blog")
    body = "Which concept was most useful in the synthetic lecture?"
    _add(
        conn,
        db.BlogPost.__table__,
        id=post,
        course_id=course,
        author_id=instructor,
        body=body,
        sha256=digest(body),
        created_at=CREATED,
    )
    for index in range(1, 11):
        student_slug = f"student-{number}-{index:02d}"
        student = _user(conn, fake, student_slug, "student")
        _add(conn, db.Enrollment.__table__, course_id=course, user_id=student, role="student")
        if index <= 8:
            answer = f"Synthetic explanation {index} for course {number}."
            _add(
                conn,
                db.Submission.__table__,
                id=fixture_id(f"{student_slug}/submission"),
                assignment_id=first,
                student_id=student,
                body_text=answer,
                extracted_text=answer,
                objective_answers={str(fixture_id(f"{first_slug}/objective")): "B"},
                sha256=digest(answer),
                submitted_at=CREATED,
            )
        if index <= 2:
            reply = f"Synthetic course discussion from student {index}."
            _add(
                conn,
                db.BlogComment.__table__,
                id=fixture_id(f"{student_slug}/comment"),
                post_id=post,
                author_id=student,
                body=reply,
                sha256=digest(reply),
                created_at=CREATED,
            )


def _seed_canaries(conn: Connection) -> None:
    def load(threat: str) -> str:
        path = FIXTURE_ROOT / "canaries" / f"{threat}.json"
        return json.loads(path.read_text(encoding="utf-8"))["text"]

    student = fixture_id("student-1-01")
    for threat in ("T06", "T13", "T20"):
        body = load(threat)
        _add(
            conn,
            db.BlogComment.__table__,
            id=fixture_id(f"canary/{threat}"),
            post_id=fixture_id("course-1/blog"),
            author_id=student,
            body=body,
            sha256=digest(body),
            created_at=CREATED,
        )

    submission = fixture_id("student-1-01/submission")
    instructor = fixture_id("instructor-1")
    course = fixture_id("course-1")
    chapter = load("T03")
    _add(
        conn,
        db.Material.__table__,
        id=fixture_id("canary/T03"),
        course_id=course,
        title="Synthetic chapter with canary",
        source_kind="third_party",
        uploader_id=instructor,
        sha256=digest(chapter),
        status="published",
    )
    for threat, student_slug in (("T07", "student-1-01"), ("T21", "student-1-02")):
        citation = f"{load(threat)} https://example.edu/rubrica-canaries/{threat.lower()}"
        _add(
            conn,
            db.Submission.__table__,
            id=fixture_id(f"canary/{threat}"),
            assignment_id=fixture_id("course-1/assignment-2"),
            student_id=fixture_id(student_slug),
            body_text=citation,
            extracted_text=citation,
            sha256=digest(citation),
            submitted_at=CREATED,
        )

    visible_answer = "A synthetic answer with a clear claim."
    _add(
        conn,
        db.Submission.__table__,
        id=fixture_id("canary/T04"),
        assignment_id=fixture_id("course-1/assignment-2"),
        student_id=fixture_id("student-1-03"),
        body_text=visible_answer,
        extracted_text=f"{visible_answer}\n{load('T04')}",
        sha256=digest(visible_answer),
        submitted_at=CREATED,
    )

    run = fixture_id("canary/T02/run")
    result_ids = [fixture_id(f"canary/T02/result-{attempt}") for attempt in (1, 2)]
    _add(
        conn,
        db.GradingRun.__table__,
        id=run,
        assignment_id=fixture_id("course-1/assignment-1"),
        started_by=instructor,
        status="completed",
        started_at=CREATED,
        ended_at=CREATED,
    )
    for attempt, result in enumerate(result_ids, start=1):
        _add(
            conn,
            db.GradingResult.__table__,
            id=result,
            run_id=run,
            submission_id=submission,
            attempt=attempt,
            scores={},
            total=2,
            feedback={},
            quotes={},
            model_id="fake",
            prompt_version="seed",
            validator_status="accepted",
            created_at=CREATED,
        )
    _add(
        conn,
        db.ProposedGrade.__table__,
        id=fixture_id("canary/T02/grade"),
        submission_id=submission,
        result_ids=result_ids,
        status="released",
        approved_by=instructor,
        approved_at=CREATED,
        released_at=CREATED,
    )
    _add(
        conn,
        db.Appeal.__table__,
        id=fixture_id("canary/T02"),
        submission_id=submission,
        student_id=student,
        reason_text=load("T02"),
        created_at=CREATED,
    )
    display_name = load("T34")
    conn.execute(
        update(db.User.__table__)
        .where(
            db.User.id == fixture_id("student-1-10"), db.User.email == "student-1-10@example.edu"
        )
        .values(display_name=display_name)
    )


def seed(conn: Connection, *, canaries: bool = False) -> None:
    # Serialize seed runs so base and opt-in fixtures are committed atomically.
    conn.execute(func.pg_advisory_xact_lock(func.hashtext("rubrica-seed-v1")))
    fake = Faker("en_US")
    fake.seed_instance(20261125)
    for number in (1, 2):
        _seed_course(conn, fake, number)
    if canaries:
        _seed_canaries(conn)


def main() -> None:
    engine = _create_engine(OWNER_ROLE, "db_owner_password")
    try:
        with engine.begin() as conn:
            seed(conn, canaries=environ.get("CANARIES") == "1")
    finally:
        engine.dispose()
    print("Loaded Rubrica synthetic demo data.")


if __name__ == "__main__":
    main()
