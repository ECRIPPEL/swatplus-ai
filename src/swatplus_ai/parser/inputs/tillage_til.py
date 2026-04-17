"""Parser for ``tillage.til`` — SWAT+ tillage-implement parameter DB.

One row per tillage implement (e.g. ``fallplow``, ``sprgplow``),
referenced from ``till`` scheduled-ops in ``management.sch``.

Columns: ``name``, 5 floats (``mix_eff``, ``mix_dp``, ``rough``,
``ridge_ht``, ``ridge_sp``), optional trailing ``description``.
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

_FLOAT_FIELDS: tuple[str, ...] = ("mix_eff", "mix_dp", "rough", "ridge_ht", "ridge_sp")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)


class TillageTilRow(BaseModel):
    """Parameters for a single tillage implement."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    mix_eff: float
    mix_dp: float
    rough: float
    ridge_ht: float
    ridge_sp: float
    description: str | None


class TillageTil(ParsedFile):
    """Contents of a ``tillage.til`` file."""

    rows: tuple[TillageTilRow, ...]

    def by_name(self, name: str) -> TillageTilRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_tillage_til(path: Path) -> TillageTil:
    """Parse a ``tillage.til`` file into a :class:`TillageTil` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[TillageTilRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return TillageTil(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> TillageTilRow:
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
    return TillageTilRow(name=name, description=description, **values)
