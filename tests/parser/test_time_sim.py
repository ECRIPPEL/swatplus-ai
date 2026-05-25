"""Tests for ``swatplus_ai.parser.inputs.time_sim``."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_missing_required_column_raises(tmp_path: Path) -> None:
    p = tmp_path / "time.sim"
    p.write_text(
        "time.sim: synthetic\nday_start yrc_start day_end yrc_end nope\n1 2000 365 2001 0\n"
    )
    with pytest.raises(ParseError, match="missing expected column"):
        parse_time_sim(p)


def test_non_integer_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "time.sim"
    p.write_text(
        "time.sim: synthetic\nday_start yrc_start day_end yrc_end step\n1 2000 365 2001 nope\n"
    )
    with pytest.raises(ParseError, match="step"):
        parse_time_sim(p)


def test_day_start_zero_accepted(tmp_path: Path) -> None:
    """SWAT+ editor v3.0+ (rev.61+) writes ``day_start=0`` / ``day_end=0``
    to mean 'simulate the full year'; the parser must accept the
    convention."""
    p = tmp_path / "time.sim"
    p.write_text("time.sim: synthetic\nday_start yrc_start day_end yrc_end step\n0 1976 0 1989 0\n")
    t = parse_time_sim(p)
    assert t.day_start == 0
    assert t.day_end == 0
    assert t.yrc_start == 1976
    assert t.yrc_end == 1989


def test_day_out_of_range_raises_parse_error(tmp_path: Path) -> None:
    """Negative days must still fail, and the error has to name the
    file + line so the user isn't stuck with a bare
    ``2 validation errors for TimeSim``."""
    p = tmp_path / "time.sim"
    p.write_text(
        "time.sim: synthetic\nday_start yrc_start day_end yrc_end step\n-1 2000 365 2001 0\n"
    )
    with pytest.raises(ParseError) as exc_info:
        parse_time_sim(p)
    assert exc_info.value.path == p
    assert exc_info.value.line_no == 3
    assert "day_start" in str(exc_info.value)
