"""Encode grade export cells so spreadsheets display them as text (C09)."""

import csv
from collections.abc import Iterable, Sequence
from io import StringIO

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(FORMULA_PREFIXES) else text


def render_csv(columns: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(_cell(column) for column in columns)
    for row in rows:
        writer.writerow(_cell(value) for value in row)
    return output.getvalue()
