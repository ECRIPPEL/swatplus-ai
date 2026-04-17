"""Parser for ``irr.ops`` — SWAT+ irrigation-operation parameter DB.

One row per irrigation method (e.g. ``sprinkler_med``), referenced
from ``irrigate`` scheduled-ops and from auto-irrigation rules.

Columns: ``name``, 7 floats (``amt_mm``, ``eff_frac``, ``sumq_frac``,
``dep_sub``, ``salt_ppm``, ``no3_ppm``, ``po4_ppm``), optional trailing
``description``.
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

_FLOAT_FIELDS: tuple[str, ...] = (
    "amt_mm",
    "eff_frac",
    "sumq_frac",
    "dep_sub",
    "salt_ppm",
    "no3_ppm",
    "po4_ppm",
)
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)


class IrrOpsRow(BaseModel):
    """Parameters for a single irrigation operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    amt_mm: float
    eff_frac: float
    sumq_frac: float
    dep_sub: float
    salt_ppm: float
    no3_ppm: float
    po4_ppm: float
    description: str | None


class IrrOps(ParsedFile):
    """Contents of an ``irr.ops`` file."""

    rows: tuple[IrrOpsRow, ...]

    def by_name(self, name: str) -> IrrOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_irr_ops(path: Path) -> IrrOps:
    """Parse an ``irr.ops`` file into an :class:`IrrOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[IrrOpsRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return IrrOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> IrrOpsRow:
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
    return IrrOpsRow(name=name, description=description, **values)
