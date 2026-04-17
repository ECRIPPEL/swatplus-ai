"""Parser for ``management.sch`` — SWAT+ operation schedules.

Nested grammar similar to ``plant.ini`` / ``soils.sol``, but each schedule
has **two** member-row types with different shapes: scheduled operations
(7 tokens, fixed dates) and auto operations (2 tokens, named
auto-schedules).

Grammar::

    title
    header                      (10 column names)
    <schedule row>              (3 tokens: name numb_ops numb_auto)
    <scheduled op row> ...      (numb_ops of them, 7 tokens each)
    <auto op row> ...           (numb_auto of them, 2 tokens each)
    <schedule row>              (next schedule)
    ...

Each schedule is referenced by ``landuse.lum.mgt``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from swatplus_ai.parser._base import (
    LineReader,
    ParseError,
    expect_tokens,
    parse_float,
    parse_int,
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "name",
    "numb_ops",
    "numb_auto",
    "op_typ",
    "mon",
    "day",
    "hu_sch",
    "op_data1",
    "op_data2",
    "op_data3",
)

_SCHEDULE_COL_COUNT = 3
_SCHEDULED_OP_COL_COUNT = 7
_AUTO_OP_COL_COUNT = 2


class ScheduledOp(BaseModel):
    """A fixed-date operation (plant, till, harvest, etc.)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    op_typ: str  # plnt, till, hvkl, fert, irrm, ...
    mon: int = Field(ge=0, le=12)
    day: int = Field(ge=0, le=31)
    hu_sch: float  # heat-unit fraction trigger
    op_data1: str | None
    op_data2: str | None
    op_data3: float


class AutoOp(BaseModel):
    """A named automatic operation (plant-harvest pair driven by PHU/date rules)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    op_typ: str  # name of the auto-operation (e.g., pl_hv_summer1)
    op_data1: str  # plant community / plant name this auto-op applies to


class ManagementSchedule(BaseModel):
    """A named management schedule (one logical entry in management.sch)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    numb_ops: int = Field(ge=0)
    numb_auto: int = Field(ge=0)
    ops: tuple[ScheduledOp, ...]
    autos: tuple[AutoOp, ...]


class ManagementSch(ParsedFile):
    """Contents of ``management.sch``: one or more named schedules."""

    schedules: tuple[ManagementSchedule, ...]

    def by_name(self, name: str) -> ManagementSchedule | None:
        for s in self.schedules:
            if s.name == name:
                return s
        return None


def _parse_scheduled_op(
    line_tokens: tuple[str, ...], *, path: Path, line_no: int, schedule_name: str
) -> ScheduledOp:
    op_typ, mon_s, day_s, hu_s, d1, d2, d3 = line_tokens
    return ScheduledOp(
        op_typ=op_typ,
        mon=parse_int(mon_s, path=path, line_no=line_no, field="mon"),
        day=parse_int(day_s, path=path, line_no=line_no, field="day"),
        hu_sch=parse_float(hu_s, path=path, line_no=line_no, field="hu_sch"),
        op_data1=parse_nullable_str(d1),
        op_data2=parse_nullable_str(d2),
        op_data3=parse_float(d3, path=path, line_no=line_no, field="op_data3"),
    )


def parse_management_sch(path: Path) -> ManagementSch:
    """Parse a ``management.sch`` file into a :class:`ManagementSch` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    schedules: list[ManagementSchedule] = []
    while not reader.eof():
        sched_line = reader.next()
        if len(sched_line.tokens) != _SCHEDULE_COL_COUNT:
            raise ParseError(
                path,
                sched_line.line_no,
                f"expected {_SCHEDULE_COL_COUNT} tokens in schedule row "
                f"(name numb_ops numb_auto), got {len(sched_line.tokens)}",
            )
        name = sched_line.tokens[0]
        ln = sched_line.line_no
        numb_ops = parse_int(sched_line.tokens[1], path=path, line_no=ln, field="numb_ops")
        numb_auto = parse_int(sched_line.tokens[2], path=path, line_no=ln, field="numb_auto")

        ops: list[ScheduledOp] = []
        for i in range(numb_ops):
            if reader.eof():
                raise ParseError(
                    path,
                    sched_line.line_no,
                    f"schedule {name!r} declares numb_ops={numb_ops} but only "
                    f"{i} scheduled-op row(s) were available before end of file",
                )
            op_line = reader.next()
            if len(op_line.tokens) != _SCHEDULED_OP_COL_COUNT:
                raise ParseError(
                    path,
                    op_line.line_no,
                    f"expected {_SCHEDULED_OP_COL_COUNT} tokens in scheduled-op row "
                    f"for schedule {name!r}, got {len(op_line.tokens)}",
                )
            ops.append(
                _parse_scheduled_op(
                    op_line.tokens, path=path, line_no=op_line.line_no, schedule_name=name
                )
            )

        autos: list[AutoOp] = []
        for i in range(numb_auto):
            if reader.eof():
                raise ParseError(
                    path,
                    sched_line.line_no,
                    f"schedule {name!r} declares numb_auto={numb_auto} but only "
                    f"{i} auto-op row(s) were available before end of file",
                )
            auto_line = reader.next()
            if len(auto_line.tokens) != _AUTO_OP_COL_COUNT:
                raise ParseError(
                    path,
                    auto_line.line_no,
                    f"expected {_AUTO_OP_COL_COUNT} tokens in auto-op row "
                    f"for schedule {name!r}, got {len(auto_line.tokens)}",
                )
            autos.append(AutoOp(op_typ=auto_line.tokens[0], op_data1=auto_line.tokens[1]))

        schedules.append(
            ManagementSchedule(
                name=name,
                numb_ops=numb_ops,
                numb_auto=numb_auto,
                ops=tuple(ops),
                autos=tuple(autos),
            )
        )

    return ManagementSch(source_path=path, title=title, schedules=tuple(schedules))
