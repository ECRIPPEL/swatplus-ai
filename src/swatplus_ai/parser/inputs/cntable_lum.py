"""Parser for ``cntable.lum`` — SWAT+ curve-number lookup table.

One row per land-use / soil-cover / condition combination (e.g.
``fal_bare``), referenced from ``landuse.lum.cn2``. Four CN values
(one per hydrologic soil group A/B/C/D) plus three short string
labels for description / treatment / condition-cover.

All rows in SWAT+ writers are exactly 8 whitespace-separated tokens:
``name``, 4 floats, and 3 single-token string labels. ``cond_cov`` is
often ``----`` for rows where a condition class does not apply; the
parser keeps it verbatim.
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

_FLOAT_FIELDS: tuple[str, ...] = ("cn_a", "cn_b", "cn_c", "cn_d")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description", "treat", "cond_cov")
_EXPECTED_TOKENS = len(_HEADER)


class CnTableLumRow(BaseModel):
    """A single curve-number lookup entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    cn_a: float
    cn_b: float
    cn_c: float
    cn_d: float
    description: str
    treat: str
    cond_cov: str


class CnTableLum(ParsedFile):
    """Contents of a ``cntable.lum`` file."""

    rows: tuple[CnTableLumRow, ...]

    def by_name(self, name: str) -> CnTableLumRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_cntable_lum(path: Path) -> CnTableLum:
    """Parse a ``cntable.lum`` file into a :class:`CnTableLum` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[CnTableLumRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return CnTableLum(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> CnTableLumRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    name, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    description, treat, cond_cov = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    return CnTableLumRow(
        name=name,
        description=description,
        treat=treat,
        cond_cov=cond_cov,
        **values,
    )
