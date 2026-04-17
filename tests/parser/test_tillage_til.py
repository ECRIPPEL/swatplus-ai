"""Tests for ``swatplus_ai.parser.inputs.tillage_til``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.tillage_til import TillageTil, parse_tillage_til


def test_parse_minimal(minimal_project: Path) -> None:
    t = parse_tillage_til(minimal_project / "tillage.til")
    assert isinstance(t, TillageTil)
    assert len(t.rows) == 2
    fp = t.by_name("fallplow")
    assert fp is not None
    assert fp.mix_eff == pytest.approx(0.95)
    assert fp.mix_dp == pytest.approx(150.0)
    assert fp.description == "genericfallplow"
    assert t.rows[1].description is None


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "tillage.til"
    p.write_text(
        "tillage.til: synthetic\n"
        "name mix_eff mix_dp rough ridge_ht NOPE description\n"
        "fallplow 0.95 150 75 0 0 desc\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_tillage_til(p)


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "tillage.til"
    p.write_text(
        "tillage.til: synthetic\n"
        "name mix_eff mix_dp rough ridge_ht ridge_sp description\n"
        "fallplow 0.95 150 75 0\n"
    )
    with pytest.raises(ParseError, match="expected at least 6 tokens"):
        parse_tillage_til(p)
