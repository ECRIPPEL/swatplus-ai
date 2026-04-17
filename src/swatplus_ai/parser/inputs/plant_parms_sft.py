"""Parser for ``plant_parms.sft`` — soft-calibration plant-parameter registry.

Nested structure: title, group count, group header ``name plants parms
nspu``, then one block per group. Each block is a group row
(``name plants parms nspu``) followed by a fixed sub-header
``var name init chg_typ neg pos lo up`` and ``plants + parms + nspu``
parameter-adjustment rows. The ``var`` column identifies which of
the three sub-classes the row belongs to; the remaining columns
declare the adjustment type (``chg_typ``), allowed deltas, and
hard bounds.
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

_GROUP_HEADER: tuple[str, ...] = ("name", "plants", "parms", "nspu")
_PARM_FIELDS: tuple[str, ...] = ("init", "chg_typ", "neg", "pos", "lo", "up")
_PARM_HEADER: tuple[str, ...] = ("var", "name", *_PARM_FIELDS)
_PARM_TOKENS = len(_PARM_HEADER)


class PlantParmsSftRow(BaseModel):
    """One plant-parameter adjustment row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    var: str
    name: str
    init: float
    chg_typ: str
    neg: float
    pos: float
    lo: float
    up: float


class PlantParmsSftGroup(BaseModel):
    """One group of plant-parameter adjustments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    plants: int
    parms: int
    nspu: int
    rows: tuple[PlantParmsSftRow, ...]


class PlantParmsSft(ParsedFile):
    """Contents of a ``plant_parms.sft`` file."""

    groups: tuple[PlantParmsSftGroup, ...]


def parse_plant_parms_sft(path: Path) -> PlantParmsSft:
    """Parse a ``plant_parms.sft`` file into a :class:`PlantParmsSft` model."""
    reader = LineReader(path)
    title = reader.next().text
    count_line = reader.next()
    if len(count_line.tokens) != 1:
        raise ParseError(
            path,
            count_line.line_no,
            f"expected single-integer group count, got {list(count_line.tokens)}",
        )
    group_count = parse_int(
        count_line.tokens[0], path=path, line_no=count_line.line_no, field="group_count"
    )
    expect_tokens(reader.next(), _GROUP_HEADER, path=path)

    groups: list[PlantParmsSftGroup] = []
    for _ in range(group_count):
        groups.append(_parse_group(reader, path=path))
    return PlantParmsSft(source_path=path, title=title, groups=tuple(groups))


def _parse_group(reader: LineReader, *, path: Path) -> PlantParmsSftGroup:
    header_line = reader.next()
    if len(header_line.tokens) != 4:
        raise ParseError(
            path,
            header_line.line_no,
            f"expected 4 tokens (name plants parms nspu), got {list(header_line.tokens)}",
        )
    ln = header_line.line_no
    name = header_line.tokens[0]
    plants = parse_int(header_line.tokens[1], path=path, line_no=ln, field="plants")
    parms = parse_int(header_line.tokens[2], path=path, line_no=ln, field="parms")
    nspu = parse_int(header_line.tokens[3], path=path, line_no=ln, field="nspu")
    expect_tokens(reader.next(), _PARM_HEADER, path=path)

    rows: list[PlantParmsSftRow] = []
    for _ in range(plants + parms + nspu):
        rows.append(_parse_row(reader.next(), path=path))
    return PlantParmsSftGroup(name=name, plants=plants, parms=parms, nspu=nspu, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> PlantParmsSftRow:
    if len(line.tokens) != _PARM_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_PARM_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    var = line.tokens[0]
    name = line.tokens[1]
    init = parse_float(line.tokens[2], path=path, line_no=ln, field="init")
    chg_typ = line.tokens[3]
    neg = parse_float(line.tokens[4], path=path, line_no=ln, field="neg")
    pos = parse_float(line.tokens[5], path=path, line_no=ln, field="pos")
    lo = parse_float(line.tokens[6], path=path, line_no=ln, field="lo")
    up = parse_float(line.tokens[7], path=path, line_no=ln, field="up")
    return PlantParmsSftRow(
        var=var, name=name, init=init, chg_typ=chg_typ, neg=neg, pos=pos, lo=lo, up=up
    )
