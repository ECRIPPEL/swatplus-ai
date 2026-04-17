"""Tests for ``swatplus_ai.parser.inputs.topography_hyd``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.topography_hyd import (
    TopographyHyd,
    parse_topography_hyd,
)


def test_parse_minimal(minimal_project: Path) -> None:
    t = parse_topography_hyd(minimal_project / "topography.hyd")
    assert isinstance(t, TopographyHyd)
    assert len(t.rows) == 3
    first = t.rows[0]
    assert first.name == "topohru00001"
    assert first.slp == pytest.approx(0.10)
    assert first.slp_len == pytest.approx(90.0)
    assert first.depos == pytest.approx(0.0)
    # Mixed HRU + routing-unit names both parse.
    assert t.by_name("toportu001") is not None
    assert t.by_name("does_not_exist") is None


def test_parse_uru(uru_project: Path) -> None:
    t = parse_topography_hyd(uru_project / "topography.hyd")
    assert len(t.rows) > 0
    # Slopes should be non-negative in any real watershed.
    for row in t.rows:
        assert row.slp >= 0.0
        assert row.slp_len > 0.0


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "topography.hyd"
    p.write_text(
        "topography.hyd: synthetic\n"
        "name slp slp_len lat_len dist_cha NOPE\n"
        "topohru001 0.1 90.0 90.0 121.0 0.0\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_topography_hyd(p)


def test_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "topography.hyd"
    p.write_text(
        "topography.hyd: synthetic\n"
        "name slp slp_len lat_len dist_cha depos\n"
        "topohru001 0.1 90.0 90.0 121.0\n"  # 5 tokens, need 6
    )
    with pytest.raises(ParseError, match="expected 6 tokens"):
        parse_topography_hyd(p)


def test_non_float_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "topography.hyd"
    p.write_text(
        "topography.hyd: synthetic\n"
        "name slp slp_len lat_len dist_cha depos\n"
        "topohru001 NOPE 90.0 90.0 121.0 0.0\n"
    )
    with pytest.raises(ParseError, match="expected float for 'slp'"):
        parse_topography_hyd(p)
