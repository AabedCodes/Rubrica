"""Index parsed course material with its server-owned source metadata."""

from collections.abc import Callable, Sequence
from hashlib import sha256
from uuid import UUID, uuid5

from sqlalchemy.dialects.postgresql import insert

from backend.db import SessionContext, session
from backend.db.models import Material, MaterialChunk
from backend.ingestion.vectors import embedded_chunks


def index_material(
    *,
    material_id: UUID,
    course_id: UUID,
    source: bytes,
    result: dict,
    embed: Callable[[str], Sequence[float]],
) -> int:
    """Index an isolated-parser result from the ingestion service's trusted job."""
    if result.get("error") or result.get("has_text_layer") is not True:
        raise ValueError("Parser did not produce usable material")
    text = result.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Parser returned empty material")

    with session("rubrica_ingest", SessionContext("system", course_id=course_id)) as db:
        material = db.get(Material, material_id)
        if material is None or material.sha256 != sha256(source).hexdigest():
            raise ValueError("Material source does not match the ingestion job")

        table = MaterialChunk.__table__
        count = 0
        for index, (chunk, vector) in enumerate(embedded_chunks(text, embed)):
            statement = (
                insert(table)
                .inline()
                .values(
                    id=uuid5(material.id, f"v{material.version}/chunk/{index}"),
                    material_id=material.id,
                    course_id=material.course_id,
                    visibility=material.status,
                    text=chunk,
                    embedding=vector,
                    source_label=material.title,
                )
            )
            statement = statement.on_conflict_do_nothing().execution_options(preserve_rowcount=True)
            count += db.connection().execute(statement).rowcount
        return count
