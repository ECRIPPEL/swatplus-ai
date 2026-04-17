"""Parser for ``graze.ops`` — SWAT+ grazing-operation parameter DB.

One row per grazing method (e.g. ``dairy_high``), referenced from
``graze`` scheduled-ops. The ``fert`` column is an FK into
``fertilizer.frt`` (the manure type deposited during grazing).

Columns: ``name``, ``fert`` (FK → fertilizer.frt), 4 floats
(``bm_eat``, ``bm_tramp``, ``man_amt``, ``grz_bm_min``), optional
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

_FLOAT_FIELDS: tuple[str, ...] = ("bm_eat", "bm_tramp", "man_amt", "grz_bm_min")
_HEADER: tuple[str, ...] = ("name", "fert", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 2 + len(_FLOAT_FIELDS)


class GrazeOpsRow(BaseModel):
    """Parameters for a single grazing operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    fert: str
    bm_eat: float
    bm_tramp: float
    man_amt: float
    grz_bm_min: float
    description: str | None


class GrazeOps(ParsedFile):
    """Contents of a ``graze.ops`` file."""

    rows: tuple[GrazeOpsRow, ...]

    def by_name(self, name: str) -> GrazeOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_graze_ops(path: Path) -> GrazeOps:
    """Parse a ``graze.ops`` file into a :class:`GrazeOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[GrazeOpsRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return GrazeOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> GrazeOpsRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens "
            f"(name + fert + {len(_FLOAT_FIELDS)} floats), got {len(line.tokens)}",
        )
    name, fert, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return GrazeOpsRow(name=name, fert=fert, description=description, **values)
