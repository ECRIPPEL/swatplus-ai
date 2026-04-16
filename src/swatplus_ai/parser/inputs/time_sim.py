"""Parser for ``time.sim`` — SWAT+ simulation period definition."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from swatplus_ai.parser._base import LineReader, expect_tokens, parse_int_row
from swatplus_ai.parser.models import ParsedFile

_HEADER = ("day_start", "yrc_start", "day_end", "yrc_end", "step")


class TimeSim(ParsedFile):
    """Contents of a ``time.sim`` file.

    Defines the simulation window as (Julian day, calendar year) pairs for
    start and end, plus an optional sub-daily timestep.
    """

    day_start: int = Field(ge=1, le=366, description="Julian day of simulation start")
    yrc_start: int = Field(description="Calendar year of simulation start")
    day_end: int = Field(ge=1, le=366, description="Julian day of simulation end")
    yrc_end: int = Field(description="Calendar year of simulation end")
    step: int = Field(ge=0, description="0 = daily; >0 = sub-daily step count")


def parse_time_sim(path: Path) -> TimeSim:
    """Parse a ``time.sim`` file into a :class:`TimeSim` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)
    values = parse_int_row(reader.next(), _HEADER, path=path)
    return TimeSim(source_path=path, title=title, **values)
