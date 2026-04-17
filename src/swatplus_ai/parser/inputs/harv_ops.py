"""Parser for ``harv.ops`` — SWAT+ harvest-operation parameter DB.

One row per harvest method (e.g. ``forest_cut``, ``grain``), referenced
from ``harvest`` / ``harv_kill`` scheduled-ops in ``management.sch``.

Columns: ``name``, ``harv_typ`` (string: ``tree``, ``grain``, ``biomass``,
…), 3 floats (``harv_idx``, ``harv_eff``, ``harv_bm_min``), optional
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

_FLOAT_FIELDS: tuple[str, ...] = ("harv_idx", "harv_eff", "harv_bm_min")
_HEADER: tuple[str, ...] = ("name", "harv_typ", *_FLOAT_FIELDS, "description")
# name + harv_typ + 3 floats = 5 minimum.
_MIN_TOKENS = 2 + len(_FLOAT_FIELDS)


class HarvOpsRow(BaseModel):
    """Parameters for a single harvest operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    harv_typ: str
    harv_idx: float
    harv_eff: float
    harv_bm_min: float
    description: str | None


class HarvOps(ParsedFile):
    """Contents of a ``harv.ops`` file."""

    rows: tuple[HarvOpsRow, ...]

    def by_name(self, name: str) -> HarvOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_harv_ops(path: Path) -> HarvOps:
    """Parse a ``harv.ops`` file into a :class:`HarvOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HarvOpsRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return HarvOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HarvOpsRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens "
            f"(name + harv_typ + {len(_FLOAT_FIELDS)} floats), got {len(line.tokens)}",
        )
    name, harv_typ, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return HarvOpsRow(name=name, harv_typ=harv_typ, description=description, **values)
