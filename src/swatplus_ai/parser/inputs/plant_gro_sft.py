"""Parser for ``plant_gro.sft`` — soft-calibration plant-growth targets.

Nested structure: title, group count, group header ``name num``, then
one block per group. Each block is a group row (``name num``) followed
by a fixed sub-header ``name yld npp lai_mx wstress astress tstress``
and ``num`` target rows. Each target row is a named plant community
and 6 expected yield / stress values.
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

_GROUP_HEADER: tuple[str, ...] = ("name", "num")
_TARGET_FIELDS: tuple[str, ...] = ("yld", "npp", "lai_mx", "wstress", "astress", "tstress")
_TARGET_HEADER: tuple[str, ...] = ("name", *_TARGET_FIELDS)
_TARGET_TOKENS = len(_TARGET_HEADER)


class PlantGroSftTarget(BaseModel):
    """One soft-calibration plant-growth target row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    yld: float
    npp: float
    lai_mx: float
    wstress: float
    astress: float
    tstress: float


class PlantGroSftGroup(BaseModel):
    """One group of plant-growth targets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    targets: tuple[PlantGroSftTarget, ...]


class PlantGroSft(ParsedFile):
    """Contents of a ``plant_gro.sft`` file."""

    groups: tuple[PlantGroSftGroup, ...]


def parse_plant_gro_sft(path: Path) -> PlantGroSft:
    """Parse a ``plant_gro.sft`` file into a :class:`PlantGroSft` model."""
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

    groups: list[PlantGroSftGroup] = []
    for _ in range(group_count):
        groups.append(_parse_group(reader, path=path))
    return PlantGroSft(source_path=path, title=title, groups=tuple(groups))


def _parse_group(reader: LineReader, *, path: Path) -> PlantGroSftGroup:
    header_line = reader.next()
    if len(header_line.tokens) != 2:
        raise ParseError(
            path,
            header_line.line_no,
            f"expected 2 tokens (name num), got {list(header_line.tokens)}",
        )
    name = header_line.tokens[0]
    num = parse_int(header_line.tokens[1], path=path, line_no=header_line.line_no, field="num")
    expect_tokens(reader.next(), _TARGET_HEADER, path=path)

    targets: list[PlantGroSftTarget] = []
    for _ in range(num):
        targets.append(_parse_target(reader.next(), path=path))
    return PlantGroSftGroup(name=name, targets=tuple(targets))


def _parse_target(line: Line, *, path: Path) -> PlantGroSftTarget:
    if len(line.tokens) != _TARGET_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_TARGET_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    float_values = {
        field: parse_float(line.tokens[i + 1], path=path, line_no=ln, field=field)
        for i, field in enumerate(_TARGET_FIELDS)
    }
    return PlantGroSftTarget(name=name, **float_values)
