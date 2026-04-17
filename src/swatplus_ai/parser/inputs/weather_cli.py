"""Parser for SWAT+ weather index files: ``pcp.cli``, ``tmp.cli``, ``slr.cli``,
``hmd.cli``, ``wnd.cli``.

All five share the same trivial shape: a title line, a one-column header
(``filename``), then one filename per line — the list of per-station
observation files the simulation should read for that variable. Stations
that use simulated (WGN) values show up as ``sim`` in
``weather-sta.cli`` instead and are not listed here.

Grammar::

    title
    filename
    <filename>
    <filename>
    ...
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser._base import LineReader, expect_tokens
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = ("filename",)


class WeatherCli(ParsedFile):
    """A list of per-station observation filenames (pcp/tmp/slr/hmd/wnd)."""

    filenames: tuple[str, ...]


def parse_weather_cli(path: Path) -> WeatherCli:
    """Parse any of the ``{pcp,tmp,slr,hmd,wnd}.cli`` index files."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    filenames: list[str] = []
    while not reader.eof():
        line = reader.next()
        filenames.append(line.tokens[0])

    return WeatherCli(source_path=path, title=title, filenames=tuple(filenames))
