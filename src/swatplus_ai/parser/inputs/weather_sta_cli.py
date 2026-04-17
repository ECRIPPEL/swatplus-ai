"""Parser for ``weather-sta.cli`` — SWAT+ weather-station wiring table.

Flat per-row shape (same pattern as ``hru-data.hru`` / ``landuse.lum``).
Each row names one weather station and wires eight references to the
actual data source used for each variable. A value is either:

    * a filename (e.g. ``02653013.pcp``) — read the observed file,
    * the literal ``sim``                 — simulate from WGN statistics,
    * the literal ``null``                — unused (parsed as ``None``).

Weather stations are referenced by ``hru-data.hru.wst``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import LineReader, ParseError, expect_tokens, parse_nullable_str
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "name",
    "wgn",
    "pcp",
    "tmp",
    "slr",
    "hmd",
    "wnd",
    "pet",
    "atmo_dep",
)

_COL_COUNT = len(_HEADER)


class WeatherStaCliRow(BaseModel):
    """A single weather-station wiring row."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    wgn: str | None  # WGN station id -> weather-wgn.cli
    pcp: str | None  # filename, "sim", or None
    tmp: str | None
    slr: str | None
    hmd: str | None
    wnd: str | None
    pet: str | None
    atmo_dep: str | None


class WeatherStaCli(ParsedFile):
    """Contents of ``weather-sta.cli``: one row per weather station."""

    rows: tuple[WeatherStaCliRow, ...]

    def by_name(self, name: str) -> WeatherStaCliRow | None:
        for r in self.rows:
            if r.name == name:
                return r
        return None


def parse_weather_sta_cli(path: Path) -> WeatherStaCli:
    """Parse a ``weather-sta.cli`` file into a :class:`WeatherStaCli` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[WeatherStaCliRow] = []
    while not reader.eof():
        line = reader.next()
        if len(line.tokens) != _COL_COUNT:
            raise ParseError(
                path,
                line.line_no,
                f"expected {_COL_COUNT} tokens in weather-sta.cli row, got {len(line.tokens)}",
            )
        name, wgn, pcp, tmp, slr, hmd, wnd, pet, atmo_dep = line.tokens
        rows.append(
            WeatherStaCliRow(
                name=name,
                wgn=parse_nullable_str(wgn),
                pcp=parse_nullable_str(pcp),
                tmp=parse_nullable_str(tmp),
                slr=parse_nullable_str(slr),
                hmd=parse_nullable_str(hmd),
                wnd=parse_nullable_str(wnd),
                pet=parse_nullable_str(pet),
                atmo_dep=parse_nullable_str(atmo_dep),
            )
        )

    return WeatherStaCli(source_path=path, title=title, rows=tuple(rows))
