"""Parser for ``object.cnt`` — SWAT+ watershed object inventory.

Single-row file (like ``codes.bsn``): title, 20-column header, one
value row. Records how many of each object type the simulation
contains (HRUs, channels, aquifers, reservoirs, recalls, exco,
delivery-ratios, canals, pumps, outlets, etc.), along with the
total landscape area.

Useful as a sanity check: a parser consuming an entire project
can cross-check these counts against its per-file parsed totals.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser._base import LineReader, ParseError, expect_tokens, parse_float, parse_int
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = ("ls_area", "tot_area")

_INT_FIELDS: tuple[str, ...] = (
    "obj",
    "hru",
    "lhru",
    "rtu",
    "gwfl",
    "aqu",
    "cha",
    "res",
    "rec",
    "exco",
    "dlr",
    "can",
    "pmp",
    "out",
    "lcha",
    "aqu2d",
    "hrd",
    "wro",
)

_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, *_INT_FIELDS)
_COL_COUNT = len(_HEADER)


class ObjectCnt(ParsedFile):
    """Contents of ``object.cnt``: one-row watershed object inventory."""

    name: str
    ls_area: float
    tot_area: float
    obj: int
    hru: int
    lhru: int
    rtu: int
    gwfl: int
    aqu: int
    cha: int
    res: int
    rec: int
    exco: int
    dlr: int
    can: int
    pmp: int
    out: int
    lcha: int
    aqu2d: int
    hrd: int
    wro: int


def parse_object_cnt(path: Path) -> ObjectCnt:
    """Parse an ``object.cnt`` file into an :class:`ObjectCnt` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    value_line = reader.next()
    if len(value_line.tokens) != _COL_COUNT:
        raise ParseError(
            path,
            value_line.line_no,
            f"expected {_COL_COUNT} tokens in object.cnt value row, got {len(value_line.tokens)}",
        )

    by_name = dict(zip(_HEADER, value_line.tokens, strict=True))
    ln = value_line.line_no

    float_values = {
        f: parse_float(by_name[f], path=path, line_no=ln, field=f) for f in _FLOAT_FIELDS
    }
    int_values = {f: parse_int(by_name[f], path=path, line_no=ln, field=f) for f in _INT_FIELDS}

    return ObjectCnt(
        source_path=path,
        title=title,
        name=by_name["name"],
        **float_values,
        **int_values,
    )
