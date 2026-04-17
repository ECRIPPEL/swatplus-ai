"""Parser for ``water_balance.sft`` — soft-calibration water-balance targets.

Nested structure: title, group count, group header ``name num``, then
one block per group. Each block is a group row (``name num``) followed
by a fixed sub-header ``name surq_rto latq_rto perc_rto et_rto
tileq_rto pet sed wyr bfr solp`` and ``num`` target rows. Each target
row is a named object (typically ``basin``) and 10 expected ratios /
annual totals the modeler wants the simulation to hit.
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
_TARGET_FIELDS: tuple[str, ...] = (
    "surq_rto",
    "latq_rto",
    "perc_rto",
    "et_rto",
    "tileq_rto",
    "pet",
    "sed",
    "wyr",
    "bfr",
    "solp",
)
_TARGET_HEADER: tuple[str, ...] = ("name", *_TARGET_FIELDS)
_TARGET_TOKENS = len(_TARGET_HEADER)


class WaterBalanceSftTarget(BaseModel):
    """One soft-calibration water-balance target row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    surq_rto: float
    latq_rto: float
    perc_rto: float
    et_rto: float
    tileq_rto: float
    pet: float
    sed: float
    wyr: float
    bfr: float
    solp: float


class WaterBalanceSftGroup(BaseModel):
    """One group (typically basin-scoped) of water-balance targets."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    targets: tuple[WaterBalanceSftTarget, ...]


class WaterBalanceSft(ParsedFile):
    """Contents of a ``water_balance.sft`` file."""

    groups: tuple[WaterBalanceSftGroup, ...]


def parse_water_balance_sft(path: Path) -> WaterBalanceSft:
    """Parse a ``water_balance.sft`` file into a :class:`WaterBalanceSft` model."""
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

    groups: list[WaterBalanceSftGroup] = []
    for _ in range(group_count):
        groups.append(_parse_group(reader, path=path))
    return WaterBalanceSft(source_path=path, title=title, groups=tuple(groups))


def _parse_group(reader: LineReader, *, path: Path) -> WaterBalanceSftGroup:
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

    targets: list[WaterBalanceSftTarget] = []
    for _ in range(num):
        targets.append(_parse_target(reader.next(), path=path))
    return WaterBalanceSftGroup(name=name, targets=tuple(targets))


def _parse_target(line: Line, *, path: Path) -> WaterBalanceSftTarget:
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
    return WaterBalanceSftTarget(name=name, **float_values)
