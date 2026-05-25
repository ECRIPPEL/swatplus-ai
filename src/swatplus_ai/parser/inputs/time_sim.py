"""Parser for ``time.sim`` — SWAT+ simulation period definition."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from swatplus_ai.parser._base import (
    LineReader,
    ParseError,
    expect_header_permissive,
    parse_int,
    record_unknown_columns,
    validate_or_raise,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER = ("day_start", "yrc_start", "day_end", "yrc_end", "step")
_FILE = "time.sim"


class TimeSim(ParsedFile):
    """Contents of a ``time.sim`` file.

    Defines the simulation window as (Julian day, calendar year) pairs for
    start and end, plus an optional sub-daily timestep.

    SWAT+ editor v3.0+ (rev.61+) writes ``day_start=0`` / ``day_end=0`` to
    mean "simulate the full calendar year" of ``yrc_start`` / ``yrc_end``
    respectively. Values in the 1..366 range still mark a specific Julian
    day. Both conventions are accepted — the zero-as-full-year convention
    is the one SWAT+ editor ships out of the box.
    """

    day_start: int = Field(
        ge=0,
        le=366,
        description="Julian day of simulation start; 0 means 'full year of yrc_start'.",
    )
    yrc_start: int = Field(description="Calendar year of simulation start")
    day_end: int = Field(
        ge=0,
        le=366,
        description="Julian day of simulation end; 0 means 'full year of yrc_end'.",
    )
    yrc_end: int = Field(description="Calendar year of simulation end")
    step: int = Field(ge=0, description="0 = daily; >0 = sub-daily step count")


def parse_time_sim(path: Path) -> TimeSim:
    """Parse a ``time.sim`` file into a :class:`TimeSim` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)
    value_line = reader.next()
    if len(value_line.tokens) != len(header_line.tokens):
        raise ParseError(
            path,
            value_line.line_no,
            f"expected {len(header_line.tokens)} values (one per header column), "
            f"got {len(value_line.tokens)}",
        )
    ln = value_line.line_no
    values = {
        name: parse_int(value_line.tokens[idx_map[name]], path=path, line_no=ln, field=name)
        for name in _HEADER
    }
    record_unknown_columns(unknowns, value_line, file=_FILE)
    return validate_or_raise(
        TimeSim,
        {"source_path": path, "title": title, **values},
        path=path,
        line_no=ln,
    )
