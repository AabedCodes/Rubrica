"""Cosine retrieval within the caller's PostgreSQL RLS transaction (C03, C24)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import isfinite
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import BlogChunk, Material, MaterialChunk

Embed = Callable[[str], Sequence[float]]


@dataclass(frozen=True, slots=True)
class Chunk:
    id: UUID
    text: str
    source_label: str
    trust: str
    material_id: UUID | None


def _query_vector(query: str, k: int, embed: Embed) -> list[float]:
    if not query.strip() or len(query) > 500 or not 1 <= k <= 8:
        raise ValueError("Invalid retrieval query or result limit")
    vector = [float(value) for value in embed(query)]
    if len(vector) != 384 or not all(map(isfinite, vector)) or not any(vector):
        raise ValueError("Expected a finite nonzero 384-dimensional vector")
    return vector


def _materials(session: Session, vector: list[float], k: int, course_id: UUID | None = None):
    distance = MaterialChunk.embedding.cosine_distance(vector)
    query = (
        select(
            MaterialChunk.id,
            MaterialChunk.text,
            MaterialChunk.source_label,
            Material.source_kind,
            MaterialChunk.material_id,
            distance,
        )
        .join(Material, Material.id == MaterialChunk.material_id)
        .where(MaterialChunk.visibility == "published", Material.status == "published")
        .order_by(distance, MaterialChunk.id)
        .limit(k)
    )
    if course_id is not None:
        query = query.where(MaterialChunk.course_id == course_id)
    return [(row[-1], Chunk(*row[:-1])) for row in session.execute(query)]


def search_for_agent(session: Session, query: str, k: int, *, embed: Embed) -> list[Chunk]:
    vector = _query_vector(query, k, embed)
    distance = BlogChunk.embedding.cosine_distance(vector)
    blog = (
        select(
            BlogChunk.id,
            BlogChunk.text,
            BlogChunk.origin,
            BlogChunk.trust,
            distance,
        )
        .order_by(distance, BlogChunk.id)
        .limit(k)
    )
    hits = _materials(session, vector, k)
    for key, text, origin, trust, score in session.execute(blog):
        label = "Instructor blog post" if origin == "post" else "Comment by a student"
        hits.append((score, Chunk(key, text, label, trust, None)))
    hits.sort(key=lambda hit: (hit[0], hit[1].id))
    return [chunk for _, chunk in hits[:k]]


def search_for_grading(
    session: Session, course_id: UUID, query: str, k: int, *, embed: Embed
) -> list[Chunk]:
    vector = _query_vector(query, k, embed)
    return [chunk for _, chunk in _materials(session, vector, k, course_id)]
