"""Index parsed course material with its server-owned source metadata."""

from collections.abc import Callable, Iterator, Sequence
from hashlib import sha256
from math import isfinite
from uuid import UUID, uuid5

from sqlalchemy.dialects.postgresql import insert

from backend.db import SessionContext, session
from backend.db.models import Material, MaterialChunk

_WINDOW = 300
_OVERLAP = 30


def _chunks(text: str) -> Iterator[str]:
    words = text.split()
    for start in range(0, len(words), _WINDOW - _OVERLAP):
        yield " ".join(words[start : start + _WINDOW])
        if start + _WINDOW >= len(words):
            break


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
        for index, chunk in enumerate(_chunks(text)):
            vector = [float(value) for value in embed(chunk)]
            if len(vector) != 384 or not all(map(isfinite, vector)) or not any(vector):
                raise ValueError("Expected a finite nonzero 384-dimensional vector")
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
