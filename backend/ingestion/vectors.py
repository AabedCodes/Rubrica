"""Chunk text and validate vectors before storage."""

from collections.abc import Callable, Iterator, Sequence
from math import isfinite

_WINDOW = 300
_OVERLAP = 30


def embedded_chunks(
    text: str, embed: Callable[[str], Sequence[float]]
) -> Iterator[tuple[str, list[float]]]:
    words = text.split()
    for start in range(0, len(words), _WINDOW - _OVERLAP):
        chunk = " ".join(words[start : start + _WINDOW])
        vector = [float(value) for value in embed(chunk)]
        if len(vector) != 384 or not all(map(isfinite, vector)) or not any(vector):
            raise ValueError("Expected a finite nonzero 384-dimensional vector")
        yield chunk, vector
        if start + _WINDOW >= len(words):
            break
