"""Tests for ``swatplus_ai.parser.inputs.weather_cli``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.weather_cli import WeatherCli, parse_weather_cli


def test_parse_minimal(minimal_project: Path) -> None:
    w = parse_weather_cli(minimal_project / "pcp.cli")
    assert isinstance(w, WeatherCli)
    assert w.filenames == ("sta001.pcp", "sta002.pcp", "sta003.pcp")


def test_parse_uru(uru_project: Path) -> None:
    w = parse_weather_cli(uru_project / "pcp.cli")
    assert len(w.filenames) > 10
    # All listed entries should look like per-station .pcp files.
    assert all(n.endswith(".pcp") for n in w.filenames)


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "pcp.cli"
    p.write_text("pcp.cli: synthetic\nNOPE\nsta001.pcp\n")
    with pytest.raises(ParseError, match="expected header"):
        parse_weather_cli(p)


def test_empty_list_is_valid(tmp_path: Path) -> None:
    # A valid title + header with zero filenames is a no-op but legal:
    # (e.g., all stations use WGN/"sim" in weather-sta.cli).
    p = tmp_path / "pcp.cli"
    p.write_text("pcp.cli: synthetic\nfilename\n")
    w = parse_weather_cli(p)
    assert w.filenames == ()
