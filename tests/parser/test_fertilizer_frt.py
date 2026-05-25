"""Tests for ``swatplus_ai.parser.inputs.fertilizer_frt``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.fertilizer_frt import (
    FertilizerFrt,
    parse_fertilizer_frt,
)


def test_parse_minimal(minimal_project: Path) -> None:
    f = parse_fertilizer_frt(minimal_project / "fertilizer.frt")
    assert isinstance(f, FertilizerFrt)
    assert len(f.rows) == 3
    urea = f.by_name("urea")
    assert urea is not None
    assert urea.min_n == pytest.approx(0.46)
    assert urea.nh3_n == pytest.approx(1.0)
    # 'null' pathogens token maps to None.
    assert urea.pathogens is None
    assert urea.description == "Urea"
    # Manure row has a non-null pathogen class.
    dairy = f.by_name("dairy_fr")
    assert dairy is not None
    assert dairy.pathogens == "fresh_manure"
    assert dairy.description == "Dairy_FreshManure"


def test_parse_uru(uru_project: Path) -> None:
    path = uru_project / "fertilizer.frt"
    if not path.is_file():
        pytest.skip("URU fixture does not yet include fertilizer.frt")
    f = parse_fertilizer_frt(path)
    assert len(f.rows) > 0
    # N+P fractions should be non-negative and at most 1.
    for row in f.rows:
        assert 0.0 <= row.min_n <= 1.0
        assert 0.0 <= row.min_p <= 1.0


def test_missing_required_column_raises(tmp_path: Path) -> None:
    p = tmp_path / "fertilizer.frt"
    p.write_text(
        "fertilizer.frt: synthetic\n"
        "name min_n min_p org_n org_p nh3_n NOPE description\n"
        "urea 0.46 0 0 0 1.0 null Urea\n"
    )
    with pytest.raises(ParseError, match="missing expected column"):
        parse_fertilizer_frt(p)


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "fertilizer.frt"
    p.write_text(
        "fertilizer.frt: synthetic\n"
        "name min_n min_p org_n org_p nh3_n pathogens description\n"
        "urea 0.46 0 0 0 1.0\n"  # 6 tokens, need >= 7
    )
    with pytest.raises(ParseError, match="expected at least 7 tokens"):
        parse_fertilizer_frt(p)


def test_non_float_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "fertilizer.frt"
    p.write_text(
        "fertilizer.frt: synthetic\n"
        "name min_n min_p org_n org_p nh3_n pathogens description\n"
        "urea NOPE 0 0 0 1.0 null Urea\n"
    )
    with pytest.raises(ParseError, match="expected float for 'min_n'"):
        parse_fertilizer_frt(p)
