"""Tests for ``swatplus_ai.parser.inputs.time_sim``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.time_sim import TimeSim, parse_time_sim


def test_parse_minimal(minimal_project: Path) -> None:
    t = parse_time_sim(minimal_project / "time.sim")
    assert isinstance(t, TimeSim)
    assert t.day_start == 1
    assert t.yrc_start == 2000
    assert t.day_end == 365
    assert t.yrc_end == 2001
    assert t.step == 0
    assert t.source_path == minimal_project / "time.sim"
    assert t.title.startswith("time.sim:")


def test_parse_uru(uru_project: Path) -> None:
    t = parse_time_sim(uru_project / "time.sim")
    assert t.day_start == 1
    assert t.yrc_start == 1976
    assert t.day_end == 365
    assert t.yrc_end == 1989
    assert t.step == 0


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "time.sim"
    p.write_text(
        "time.sim: synthetic\nday_start yrc_start day_end yrc_end nope\n1 2000 365 2001 0\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_time_sim(p)


def test_non_integer_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "time.sim"
    p.write_text(
        "time.sim: synthetic\nday_start yrc_start day_end yrc_end step\n1 2000 365 2001 nope\n"
    )
    with pytest.raises(ParseError, match="step"):
        parse_time_sim(p)


def test_day_out_of_range_raises(tmp_path: Path) -> None:
    p = tmp_path / "time.sim"
    p.write_text(
        "time.sim: synthetic\nday_start yrc_start day_end yrc_end step\n0 2000 365 2001 0\n"
    )
    with pytest.raises(ValidationError):
        parse_time_sim(p)
