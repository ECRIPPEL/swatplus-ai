"""Parser for ``cons_practice.lum`` — SWAT+ conservation-practice lookup.

One row per conservation practice (e.g. ``up_down_slope``,
``cross_slope``), referenced from ``landuse.lum.cons_practice``.

Columns: ``name``, 2 floats (``usle_p``, ``slp_len_max``), optional
trailing ``description``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_float,
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = ("usle_p", "slp_len_max")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)


class ConsPracticeLumRow(BaseModel):
    """Parameters for a single conservation practice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    usle_p: float
    slp_len_max: float
    description: str | None


class ConsPracticeLum(ParsedFile):
    """Contents of a ``cons_practice.lum`` file."""

    rows: tuple[ConsPracticeLumRow, ...]

    def by_name(self, name: str) -> ConsPracticeLumRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_cons_practice_lum(path: Path) -> ConsPracticeLum:
    """Parse a ``cons_practice.lum`` file into a :class:`ConsPracticeLum` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[ConsPracticeLumRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return ConsPracticeLum(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> ConsPracticeLumRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens "
            f"(name + {len(_FLOAT_FIELDS)} floats), got {len(line.tokens)}",
        )
    name, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return ConsPracticeLumRow(name=name, description=description, **values)
