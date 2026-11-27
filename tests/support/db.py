"""Disposable database fixture for RLS and verification tests (B1, B4).

Needs a throwaway PostgreSQL 18 + pgvector with trust auth, a `rubrica`
database and a `rubrica_owner` superuser:
- `make test-db-up` starts one on 127.0.0.1:55432;
- CI runs one as a service container.
Set RUBRICA_D1_TEST_PORT (the variable D1's tests already use) to its port.
Tests that need it skip when it isn't set.

The fixture migrates to head, seeds a small two-course world, yields it and
downgrades to base at module end, so each test module starts from an empty
database (D1's own tests require that).

Runtime roles connect through `backend.db.session.session()`, the same helper
the services use, so the tests exercise the real transaction-local RLS context.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib import import_module
from uuid import UUID, uuid4

import pytest

NOW = datetime(2026, 11, 28, tzinfo=UTC)
KEY_TEXT = "KEYMARK-b4c1"  # answer-key content; must never be readable by student contexts


@dataclass
class World:
    """IDs of the seeded rows, plus helpers to query as a role."""

    ids: dict[str, UUID]
    engines: dict[str, object] = field(repr=False)
    owner: object = field(repr=False)
    _patch: pytest.MonkeyPatch = field(repr=False)

    @contextmanager
    def as_role(self, role: str, ctx) -> Iterator[object]:
        """A transaction as `role` with RLS settings from `ctx` (backend.db.SessionContext)."""
        from backend.db import session

        self._patch.setenv("DB_ROLE", role)
        with session(role, ctx) as db:
            yield db

    @contextmanager
    def raw(self, role: str) -> Iterator[object]:
        """A connection as `role` with NO RLS settings (fail-closed checks)."""
        engine = self.engines_for(role)
        with engine.connect() as conn:
            yield conn
            conn.rollback()

    def engines_for(self, role: str):
        from sqlalchemy import create_engine

        if role not in self.engines:
            url = self.owner.url.set(username=role)
            self.engines[role] = create_engine(
                url, hide_parameters=True, pool_size=1, max_overflow=0
            )
        return self.engines[role]


def _seed(conn) -> dict[str, UUID]:
    from sqlalchemy import insert

    from backend.db.models import (
        AnswerKey,
        Assignment,
        BlogChunk,
        BlogPost,
        Course,
        Enrollment,
        GradingResult,
        GradingRun,
        ProposedGrade,
        RubricCriterion,
        Submission,
        User,
    )

    ids: dict[str, UUID] = {}

    def add(name: str, model, **values) -> UUID:
        key = uuid4()
        conn.execute(insert(model.__table__).inline().values(id=key, **values))
        ids[name] = key
        return key

    def user(name: str, role: str) -> UUID:
        return add(
            name, User, email=f"{name}@example.edu", display_name=name, role=role, password_hash="!"
        )  # synthetic users only, no real password hashes

    c1 = add("course1", Course, code="SEC101", title="Course 1")
    c2 = add("course2", Course, code="SEC202", title="Course 2")
    inst1 = user("instructor1", "instructor")
    inst2 = user("instructor2", "instructor")
    alice = user("alice", "student")  # course 1
    bob = user("bob", "student")  # course 1
    carol = user("carol", "student")  # course 2 only
    conn.execute(
        insert(Enrollment),
        [
            {"course_id": c1, "user_id": inst1, "role": "instructor"},
            {"course_id": c1, "user_id": alice, "role": "student"},
            {"course_id": c1, "user_id": bob, "role": "student"},
            {"course_id": c2, "user_id": inst2, "role": "instructor"},
            {"course_id": c2, "user_id": carol, "role": "student"},
        ],
    )

    def assignment(name: str, course: UUID, by: UUID) -> UUID:
        return add(
            name,
            Assignment,
            course_id=course,
            title=name,
            instructions="",
            due_at=NOW,
            status="published",
            created_by=by,
        )

    a1 = assignment("a1", c1, inst1)  # graded in run1
    a2 = assignment("a2", c1, inst1)  # graded in run2
    a3 = assignment("a3", c2, inst2)  # other course
    crit = add(
        "criterion_a1",
        RubricCriterion,
        assignment_id=a1,
        label="Open",
        max_points=4,
        kind="open",
        position=0,
    )
    add(
        "answer_key_a1",
        AnswerKey,
        assignment_id=a1,
        criterion_id=crit,
        content=KEY_TEXT,
        status="approved",
        approved_by=inst1,
    )

    def submission(name: str, a: UUID, student: UUID) -> UUID:
        return add(
            name,
            Submission,
            assignment_id=a,
            student_id=student,
            body_text="Synthetic answer",
            sha256="test",
        )

    s_alice_a1 = submission("s_alice_a1", a1, alice)
    s_bob_a1 = submission("s_bob_a1", a1, bob)
    s_alice_a2 = submission("s_alice_a2", a2, alice)
    s_carol_a3 = submission("s_carol_a3", a3, carol)

    run1 = add("run1", GradingRun, assignment_id=a1, started_by=inst1, status="running")
    run2 = add("run2", GradingRun, assignment_id=a2, started_by=inst1, status="running")
    run3 = add("run3", GradingRun, assignment_id=a3, started_by=inst2, status="running")

    def result(name: str, run: UUID, sub: UUID) -> UUID:
        return add(
            name,
            GradingResult,
            run_id=run,
            submission_id=sub,
            attempt=1,
            model_id="fake",
            prompt_version="test",
            validator_status="accepted",
        )

    r_alice_a1 = result("r_alice_a1", run1, s_alice_a1)
    r_bob_a1 = result("r_bob_a1", run1, s_bob_a1)
    r_alice_a2 = result("r_alice_a2", run2, s_alice_a2)
    r_carol_a3 = result("r_carol_a3", run3, s_carol_a3)

    def grade(name: str, sub: UUID, res: UUID, status: str, by: UUID) -> UUID:
        extra = {}
        if status == "released":
            extra = {"approved_by": by, "approved_at": NOW, "released_at": NOW}
        return add(name, ProposedGrade, submission_id=sub, result_ids=[res], status=status, **extra)

    # alice sees exactly one grade: her own released one.
    grade("g_alice_a1_released", s_alice_a1, r_alice_a1, "released", inst1)
    grade("g_bob_a1_released", s_bob_a1, r_bob_a1, "released", inst1)  # another student's
    grade("g_alice_a2_pending", s_alice_a2, r_alice_a2, "pending", inst1)  # hers, not released
    grade("g_carol_a3_released", s_carol_a3, r_carol_a3, "released", inst2)  # other course

    embedding = [1.0, *([0.0] * 383)]
    for course, name in ((c1, "post_c1"), (c2, "post_c2")):
        by = inst1 if course == c1 else inst2
        post = add(name, BlogPost, course_id=course, author_id=by, body=name, sha256="test")
        add(
            f"chunk_{name}",
            BlogChunk,
            course_id=course,
            origin="post",
            origin_id=post,
            author_id=by,
            trust="instructor",
            text=name,
            embedding=embedding,
        )
    return ids


@pytest.fixture(scope="module")
def rubrica_db() -> Iterator[World]:
    port = os.environ.get("RUBRICA_D1_TEST_PORT")
    if not port:
        pytest.skip("needs a disposable PostgreSQL (make test-db-up; RUBRICA_D1_TEST_PORT)")

    from alembic import command
    from sqlalchemy import URL, create_engine, inspect, text

    from backend.db.migrate import migration_config

    owner = create_engine(
        URL.create(
            "postgresql+psycopg",
            username="rubrica_owner",
            host="127.0.0.1",
            port=int(port),
            database="rubrica",
        ),
        hide_parameters=True,
    )
    session_module = import_module("backend.db.session")
    engines: dict[str, object] = {}
    world: World | None = None
    config = migration_config()
    upgraded = False
    patch = pytest.MonkeyPatch()
    try:
        # Trust auth: role passwords are irrelevant; the canary marks the fake value (T-19).
        patch.setattr(session_module, "_read_password", lambda _name: "CANARY-T19-b4d1")
        world = World(ids={}, engines=engines, owner=owner, _patch=patch)
        patch.setattr(session_module, "_runtime_engine", world.engines_for)
        with owner.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            assert tables <= {"alembic_version"}, "RLS tests need an empty database"
            conn.rollback()
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
            upgraded = True
        with owner.begin() as conn:
            world.ids = _seed(conn)
            conn.execute(text("SELECT 1"))
        yield world
    finally:
        for engine in engines.values():
            engine.dispose()
        if upgraded:
            with owner.connect() as conn:
                config.attributes["connection"] = conn
                command.downgrade(config, "base")
        owner.dispose()
        patch.undo()
