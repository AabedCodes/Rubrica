"""Per-service connections and transaction-local RLS context (C31)."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from os import environ
from pathlib import Path
from typing import Literal
from uuid import UUID

from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.orm import Session

RUNTIME_ROLES = {
    "rubrica_web": "db_web_password",
    "rubrica_ingest": "db_ingest_password",
    "rubrica_grading": "db_grading_password",
    "rubrica_mcp": "db_mcp_password",
    "rubrica_release": "db_release_password",
    "rubrica_fetch": "db_fetch_password",
}
OWNER_ROLE = "rubrica_owner"
SECRET_DIR = Path("/run/secrets")

ActorKind = Literal["student", "instructor", "grading_run", "system"]


@dataclass(frozen=True, slots=True)
class SessionContext:
    """Identity supplied by verified session, capability token or internal job."""

    actor_kind: ActorKind
    user_id: UUID | None = None
    course_id: UUID | None = None
    run_id: UUID | None = None

    def __post_init__(self) -> None:
        match self.actor_kind:
            case "student" | "instructor":
                valid = self.user_id is not None and self.run_id is None
            case "grading_run":
                valid = self.run_id is not None and self.course_id is not None
                valid = valid and self.user_id is None
            case "system":
                valid = self.user_id is None and self.run_id is None
            case _:
                valid = False
        if not valid:
            raise ValueError("Invalid database session context")


def _read_password(filename: str) -> str:
    password = (SECRET_DIR / filename).read_text(encoding="utf-8").rstrip("\r\n")
    if not password:
        raise ValueError(f"Empty database password file: {filename}")
    return password


def _create_engine(role: str, filename: str) -> Engine:
    url = URL.create(
        "postgresql+psycopg",
        username=role,
        password=_read_password(filename),
        host=environ.get("POSTGRES_HOST", "db"),
        port=int(environ.get("POSTGRES_PORT", "5432")),
        database=environ.get("POSTGRES_DB", "rubrica"),
    )
    return create_engine(url, hide_parameters=True, pool_pre_ping=True)


@cache
def _runtime_engine(role: str) -> Engine:
    return _create_engine(role, RUNTIME_ROLES[role])


_SET_CONTEXT = text("""
    SELECT set_config('rubrica.actor_kind', :actor_kind, true),
           set_config('rubrica.user_id', :user_id, true),
           set_config('rubrica.course_id', :course_id, true),
           set_config('rubrica.run_id', :run_id, true)
""")


@contextmanager
def session(role: str, ctx: SessionContext) -> Iterator[Session]:
    """Open a transaction using the role assigned to this service in Compose."""
    if role not in RUNTIME_ROLES or role != environ.get("DB_ROLE"):
        raise ValueError("Database role is unavailable to this service")

    with Session(_runtime_engine(role)) as db, db.begin():
        db.execute(
            _SET_CONTEXT,
            {
                "actor_kind": ctx.actor_kind,
                "user_id": str(ctx.user_id) if ctx.user_id is not None else "",
                "course_id": str(ctx.course_id) if ctx.course_id is not None else "",
                "run_id": str(ctx.run_id) if ctx.run_id is not None else "",
            },
        )
        yield db
