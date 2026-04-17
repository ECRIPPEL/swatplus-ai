"""Parser for ``weather-wgn.cli`` — SWAT+ weather-generator monthly statistics.

Unlike the other files, ``weather-wgn.cli`` has **no file-level column
header**. Each station carries its own embedded column header followed
by exactly 12 monthly rows (one row per calendar month, Jan-Dec).

Grammar::

    title
    <station header>            (5 tokens: name lat lon elev rain_yrs)
    <monthly col header>        (14 names)
    <monthly row> x 12          (14 floats each)
    <station header>            (next station)
    ...

Stations are referenced by ``weather-sta.cli.wgn``.
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
)
from swatplus_ai.parser.models import ParsedFile

_MONTHLY_HEADER: tuple[str, ...] = (
    "tmp_max_ave",
    "tmp_min_ave",
    "tmp_max_sd",
    "tmp_min_sd",
    "pcp_ave",
    "pcp_sd",
    "pcp_skew",
    "wet_dry",
    "wet_wet",
    "pcp_days",
    "pcp_hhr",
    "slr_ave",
    "dew_ave",
    "wnd_ave",
)

_STATION_COL_COUNT = 5
_MONTHLY_COL_COUNT = len(_MONTHLY_HEADER)
_MONTHS_PER_STATION = 12


class WgnMonth(BaseModel):
    """Monthly climate statistics for one month of one WGN station."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tmp_max_ave: float
    tmp_min_ave: float
    tmp_max_sd: float
    tmp_min_sd: float
    pcp_ave: float
    pcp_sd: float
    pcp_skew: float
    wet_dry: float  # P(wet day | prior dry day)
    wet_wet: float  # P(wet day | prior wet day)
    pcp_days: float  # avg # of wet days per month
    pcp_hhr: float  # avg half-hour rainfall
    slr_ave: float
    dew_ave: float
    wnd_ave: float


class WgnStation(BaseModel):
    """One WGN station: location + rain_yrs + 12 monthly stats."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    lat: float
    lon: float
    elev: float
    rain_yrs: int = Field(ge=0, description="Years of rainfall data used for the stats")
    months: tuple[WgnMonth, ...]


class WeatherWgnCli(ParsedFile):
    """Contents of ``weather-wgn.cli``: one or more WGN stations."""

    stations: tuple[WgnStation, ...]

    def by_name(self, name: str) -> WgnStation | None:
        for s in self.stations:
            if s.name == name:
                return s
        return None


def _parse_monthly_row(
    tokens: tuple[str, ...], *, path: Path, line_no: int, station_name: str
) -> WgnMonth:
    values = [
        parse_float(tok, path=path, line_no=line_no, field=name)
        for name, tok in zip(_MONTHLY_HEADER, tokens, strict=True)
    ]
    return WgnMonth(**dict(zip(_MONTHLY_HEADER, values, strict=True)))


def parse_weather_wgn_cli(path: Path) -> WeatherWgnCli:
    """Parse a ``weather-wgn.cli`` file into a :class:`WeatherWgnCli` model."""
    reader = LineReader(path)
    title = reader.next().text

    stations: list[WgnStation] = []
    while not reader.eof():
        sta_line = reader.next()
        if len(sta_line.tokens) != _STATION_COL_COUNT:
            raise ParseError(
                path,
                sta_line.line_no,
                f"expected {_STATION_COL_COUNT} tokens in WGN station row "
                f"(name lat lon elev rain_yrs), got {len(sta_line.tokens)}",
            )
        name, lat_s, lon_s, elev_s, rain_yrs_s = sta_line.tokens
        ln = sta_line.line_no

        if reader.eof():
            raise ParseError(
                path,
                sta_line.line_no,
                f"station {name!r} is missing its monthly column header",
            )
        expect_tokens(reader.next(), _MONTHLY_HEADER, path=path)

        months: list[WgnMonth] = []
        for i in range(_MONTHS_PER_STATION):
            if reader.eof():
                raise ParseError(
                    path,
                    sta_line.line_no,
                    f"station {name!r} has only {i} monthly row(s), expected {_MONTHS_PER_STATION}",
                )
            m_line = reader.next()
            if len(m_line.tokens) != _MONTHLY_COL_COUNT:
                raise ParseError(
                    path,
                    m_line.line_no,
                    f"expected {_MONTHLY_COL_COUNT} tokens in monthly row for "
                    f"station {name!r}, got {len(m_line.tokens)}",
                )
            months.append(
                _parse_monthly_row(
                    m_line.tokens, path=path, line_no=m_line.line_no, station_name=name
                )
            )

        stations.append(
            WgnStation(
                name=name,
                lat=parse_float(lat_s, path=path, line_no=ln, field="lat"),
                lon=parse_float(lon_s, path=path, line_no=ln, field="lon"),
                elev=parse_float(elev_s, path=path, line_no=ln, field="elev"),
                rain_yrs=parse_int(rain_yrs_s, path=path, line_no=ln, field="rain_yrs"),
                months=tuple(months),
            )
        )

    return WeatherWgnCli(source_path=path, title=title, stations=tuple(stations))
