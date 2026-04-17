"""Tests for ``swatplus_ai.parser.inputs.weather_sta_cli``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.weather_sta_cli import WeatherStaCli, parse_weather_sta_cli


def test_parse_minimal(minimal_project: Path) -> None:
    w = parse_weather_sta_cli(minimal_project / "weather-sta.cli")
    assert isinstance(w, WeatherStaCli)
    assert len(w.rows) == 2

    sta1 = w.rows[0]
    assert sta1.name == "sta001"
    assert sta1.wgn == "wgn001"
    assert sta1.pcp == "sta001.pcp"
    assert sta1.tmp == "sim"
    assert sta1.pet is None  # "null" -> None
    assert sta1.atmo_dep is None

    sta2 = w.rows[1]
    assert sta2.name == "sta002"
    assert sta2.pcp == "sim"  # no observed file; simulated via WGN

    assert w.by_name("sta002") is sta2
    assert w.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    w = parse_weather_sta_cli(uru_project / "weather-sta.cli")
    assert len(w.rows) > 10
    # Names must be unique so hru-data.hru.wst references resolve uniquely.
    names = [r.name for r in w.rows]
    assert len(set(names)) == len(names)
    # Every row must point at a WGN entry (URU relies on WGN for at least one var).
    assert all(r.wgn is not None for r in w.rows)


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "weather-sta.cli"
    p.write_text(
        "weather-sta.cli: synthetic\n"
        "name wgn pcp tmp slr hmd wnd pet NOPE\n"
        "s1 w1 null null null null null null null\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_weather_sta_cli(p)


def test_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "weather-sta.cli"
    p.write_text(
        "weather-sta.cli: synthetic\n"
        "name wgn pcp tmp slr hmd wnd pet atmo_dep\n"
        "s1 w1 null null null null null null\n"  # 8, need 9
    )
    with pytest.raises(ParseError, match="expected 9 tokens"):
        parse_weather_sta_cli(p)
