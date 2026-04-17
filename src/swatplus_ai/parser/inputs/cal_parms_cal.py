"""Parser for ``cal_parms.cal`` — master calibratable-parameter registry.

One row per parameter the SWAT+ calibration engine is allowed to touch.
File starts with the usual title line, then a single integer count of
rows, then the header ``name obj_typ abs_min abs_max units``. Each row
declares the parameter's name, the object class it applies to (``hru``,
``sol``, ``aqu``, ...), the absolute legal range (``abs_min``,
``abs_max``), and a units label (may be the literal ``null``).
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
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = ("name", "obj_typ", "abs_min", "abs_max", "units")
_EXPECTED_TOKENS = len(_HEADER)


class CalParmsCalRow(BaseModel):
    """One calibratable-parameter registry entry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    obj_typ: str
    abs_min: float
    abs_max: float
    units: str | None


class CalParmsCal(ParsedFile):
    """Contents of a ``cal_parms.cal`` file."""

    rows: tuple[CalParmsCalRow, ...]

    def by_name(self, name: str) -> CalParmsCalRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_cal_parms_cal(path: Path) -> CalParmsCal:
    """Parse a ``cal_parms.cal`` file into a :class:`CalParmsCal` model."""
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

    rows: list[CalParmsCalRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    if len(rows) != expected_count:
        raise ParseError(
            path,
            count_line.line_no,
            f"header declared {expected_count} rows, found {len(rows)}",
        )
    return CalParmsCal(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> CalParmsCalRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    obj_typ = line.tokens[1]
    abs_min = parse_float(line.tokens[2], path=path, line_no=ln, field="abs_min")
    abs_max = parse_float(line.tokens[3], path=path, line_no=ln, field="abs_max")
    units = parse_nullable_str(line.tokens[4])
    return CalParmsCalRow(name=name, obj_typ=obj_typ, abs_min=abs_min, abs_max=abs_max, units=units)
