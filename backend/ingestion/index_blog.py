"""Index stored blog posts and comments in their separate collection (C24)."""

from collections.abc import Callable, Sequence
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from backend.db import SessionContext, session
from backend.db.models import BlogChunk
from backend.ingestion.vectors import embedded_chunks


def index_blog(
    *,
    origin: str,
    origin_id: UUID,
    course_id: UUID,
    embed: Callable[[str], Sequence[float]],
) -> int:
    if origin not in {"post", "comment"}:
        raise ValueError("Unknown blog origin")
    with session("rubrica_ingest", SessionContext("system", course_id=course_id)) as db:
        source = db.execute(
            text("SELECT * FROM public.blog_index_source(:origin, :id)"),
            {"origin": origin, "id": origin_id},
        ).one_or_none()
        if source is None:
            return 0
        count = 0
        for number, (chunk, vector) in enumerate(embedded_chunks(source.body, embed)):
            statement = (
                insert(BlogChunk.__table__)
                .inline()
                .values(
                    id=uuid5(origin_id, f"blog/{origin}/{number}"),
                    course_id=course_id,
                    origin=origin,
                    origin_id=origin_id,
                    author_id=source.author_id,
                    trust="instructor" if origin == "post" else "untrusted",
                    text=chunk,
                    embedding=vector,
                )
                .on_conflict_do_nothing()
                .execution_options(preserve_rowcount=True)
            )
            count += db.connection().execute(statement).rowcount
        return count
