"""Parser for ``aqu_catunit.ele`` — SWAT+ aquifer catchment-unit elements.

One row per aquifer listing its fractional contribution to the basin /
subbasin / region at aquifer-group scale. The row shape matches
``ls_unit.ele``: ``id name obj_typ obj_typ_no bsn_frac sub_frac reg_frac``.
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
    parse_int,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "id",
    "name",
    "obj_typ",
    "obj_typ_no",
    "bsn_frac",
    "sub_frac",
    "reg_frac",
)
_EXPECTED_TOKENS = len(_HEADER)


class AquCatunitEleRow(BaseModel):
    """One aquifer catchment-unit element entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    obj_typ: str
    obj_typ_no: int
    bsn_frac: float
    sub_frac: float
    reg_frac: float


class AquCatunitEle(ParsedFile):
    """Contents of an ``aqu_catunit.ele`` file."""

    rows: tuple[AquCatunitEleRow, ...]

    def by_name(self, name: str) -> AquCatunitEleRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_aqu_catunit_ele(path: Path) -> AquCatunitEle:
    """Parse an ``aqu_catunit.ele`` file into an :class:`AquCatunitEle` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[AquCatunitEleRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return AquCatunitEle(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> AquCatunitEleRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    t = line.tokens
    ln = line.line_no
    return AquCatunitEleRow(
        id=parse_int(t[0], path=path, line_no=ln, field="id"),
        name=t[1],
        obj_typ=t[2],
        obj_typ_no=parse_int(t[3], path=path, line_no=ln, field="obj_typ_no"),
        bsn_frac=parse_float(t[4], path=path, line_no=ln, field="bsn_frac"),
        sub_frac=parse_float(t[5], path=path, line_no=ln, field="sub_frac"),
        reg_frac=parse_float(t[6], path=path, line_no=ln, field="reg_frac"),
    )
