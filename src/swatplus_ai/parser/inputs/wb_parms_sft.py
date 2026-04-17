"""Parser for ``wb_parms.sft`` — water-balance soft-calibration parameters.

Title line, then a single integer count of rows, then the header
``name chg_typ neg pos lo up``. Each row names a parameter the
soft-calibration engine may nudge, the change type (``pctchg``,
``abschg``, ``absval``), allowed negative/positive deltas, and the
hard lower/upper bounds.
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

_FLOAT_FIELDS: tuple[str, ...] = ("neg", "pos", "lo", "up")
_HEADER: tuple[str, ...] = ("name", "chg_typ", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class WbParmsSftRow(BaseModel):
    """One water-balance soft-calibration parameter entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    chg_typ: str
    neg: float
    pos: float
    lo: float
    up: float


class WbParmsSft(ParsedFile):
    """Contents of a ``wb_parms.sft`` file."""

    rows: tuple[WbParmsSftRow, ...]

    def by_name(self, name: str) -> WbParmsSftRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_wb_parms_sft(path: Path) -> WbParmsSft:
    """Parse a ``wb_parms.sft`` file into a :class:`WbParmsSft` model."""
    reader = LineReader(path)
    title = reader.next().text
    count_line = reader.next()
    if len(count_line.tokens) != 1:
        raise ParseError(
            path,
            count_line.line_no,
            f"expected single-integer row count, got {list(count_line.tokens)}",
        )
    expected_count = parse_int(
        count_line.tokens[0], path=path, line_no=count_line.line_no, field="row_count"
    )
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[WbParmsSftRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    if len(rows) != expected_count:
        raise ParseError(
            path,
            count_line.line_no,
            f"header declared {expected_count} rows, found {len(rows)}",
        )
    return WbParmsSft(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> WbParmsSftRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    chg_typ = line.tokens[1]
    float_values = {
        field: parse_float(line.tokens[i + 2], path=path, line_no=ln, field=field)
        for i, field in enumerate(_FLOAT_FIELDS)
    }
    return WbParmsSftRow(name=name, chg_typ=chg_typ, **float_values)
