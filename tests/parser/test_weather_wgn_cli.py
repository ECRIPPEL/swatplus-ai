"""Tests for ``swatplus_ai.parser.inputs.weather_wgn_cli``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.weather_wgn_cli import WeatherWgnCli, parse_weather_wgn_cli


def test_parse_minimal(minimal_project: Path) -> None:
    w = parse_weather_wgn_cli(minimal_project / "weather-wgn.cli")
    assert isinstance(w, WeatherWgnCli)
    assert len(w.stations) == 2

    s1 = w.stations[0]
    assert s1.name == "wgn001"
    assert s1.lat == pytest.approx(-26.9017)
    assert s1.lon == pytest.approx(-50.6592)
    assert s1.elev == pytest.approx(1067.0)
    assert s1.rain_yrs == 32
    assert len(s1.months) == 12

    jan = s1.months[0]
    assert jan.tmp_max_ave == pytest.approx(24.5)
    assert jan.pcp_ave == pytest.approx(176.0)
    assert jan.wnd_ave == pytest.approx(2.3)

    assert w.by_name("wgn002") is w.stations[1]
    assert w.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    w = parse_weather_wgn_cli(uru_project / "weather-wgn.cli")
    assert len(w.stations) > 10
    # Every station carries exactly 12 months of stats.
    for s in w.stations:
        assert len(s.months) == 12
        assert s.rain_yrs >= 0


def test_station_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "weather-wgn.cli"
    p.write_text(
        "weather-wgn.cli: synthetic\nwgn1 -26 -50 100\n"  # 4 tokens, need 5
    )
    with pytest.raises(ParseError, match="WGN station row"):
        parse_weather_wgn_cli(p)


def test_missing_monthly_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "weather-wgn.cli"
    p.write_text(
        "weather-wgn.cli: synthetic\n"
        "wgn1 -26 -50 100 32\n"
        "NOPE tmp_min_ave tmp_max_sd tmp_min_sd pcp_ave pcp_sd pcp_skew wet_dry "
        "wet_wet pcp_days pcp_hhr slr_ave dew_ave wnd_ave\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_weather_wgn_cli(p)


def test_fewer_than_12_monthly_rows_raises(tmp_path: Path) -> None:
    p = tmp_path / "weather-wgn.cli"
    p.write_text(
        "weather-wgn.cli: synthetic\n"
        "wgn1 -26 -50 100 32\n"
        "tmp_max_ave tmp_min_ave tmp_max_sd tmp_min_sd pcp_ave pcp_sd pcp_skew "
        "wet_dry wet_wet pcp_days pcp_hhr slr_ave dew_ave wnd_ave\n"
        "24 15 3 2 176 13 1 0.28 0.51 11 29 20 17 2\n"
        # only 1 monthly row, need 12
    )
    with pytest.raises(ParseError, match="monthly row"):
        parse_weather_wgn_cli(p)


def test_monthly_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "weather-wgn.cli"
    content = (
        "weather-wgn.cli: synthetic\n"
        "wgn1 -26 -50 100 32\n"
        "tmp_max_ave tmp_min_ave tmp_max_sd tmp_min_sd pcp_ave pcp_sd pcp_skew "
        "wet_dry wet_wet pcp_days pcp_hhr slr_ave dew_ave wnd_ave\n"
    )
    # 11 full rows + 1 short (13 tokens)
    content += "24 15 3 2 176 13 1 0.28 0.51 11 29 20 17 2\n" * 11
    content += "24 15 3 2 176 13 1 0.28 0.51 11 29 20 17\n"
    p.write_text(content)
    with pytest.raises(ParseError, match="monthly row"):
        parse_weather_wgn_cli(p)
