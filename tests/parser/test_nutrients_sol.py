"""Tests for ``swatplus_ai.parser.inputs.nutrients_sol``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.nutrients_sol import (
    NutrientsSol,
    parse_nutrients_sol,
)


def test_parse_minimal(minimal_project: Path) -> None:
    n = parse_nutrients_sol(minimal_project / "nutrients.sol")
    assert isinstance(n, NutrientsSol)
    assert len(n.rows) == 2
    first = n.rows[0]
    assert first.name == "soilnut1"
    assert first.dp_co == pytest.approx(13.0)
    assert first.tot_n == pytest.approx(6.0)
    assert first.bray_p == pytest.approx(0.85)
    # Trailing free-text description is joined across tokens.
    assert first.description == "default nutrients"
    # Absent description collapses to None.
    assert n.rows[1].description is None
    assert n.by_name("soilnut1") is not None
    assert n.by_name("nope") is None


def test_parse_uru(uru_project: Path) -> None:
    path = uru_project / "nutrients.sol"
    if not path.is_file():
        pytest.skip("URU fixture does not yet include nutrients.sol")
    n = parse_nutrients_sol(path)
    assert len(n.rows) > 0
    for row in n.rows:
        # All nutrient values should be non-negative in any real parameter set.
        assert row.tot_n >= 0
        assert row.tot_p >= 0


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "nutrients.sol"
    p.write_text(
        "nutrients.sol: synthetic\n"
        "name dp_co tot_n min_n org_n tot_p min_p org_p sol_p h3a_p mehl_p NOPE description\n"
        "soilnut1 13 6 3 3 3.5 0.4 0.15 0.25 1.2 0.85 0.85\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_nutrients_sol(p)


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "nutrients.sol"
    p.write_text(
        "nutrients.sol: synthetic\n"
        "name dp_co tot_n min_n org_n tot_p min_p org_p sol_p h3a_p mehl_p bray_p description\n"
        "soilnut1 13 6 3 3 3.5 0.4 0.15 0.25 1.2 0.85\n"  # 11 tokens, need >= 12
    )
    with pytest.raises(ParseError, match="expected at least 12 tokens"):
        parse_nutrients_sol(p)


def test_non_float_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "nutrients.sol"
    p.write_text(
        "nutrients.sol: synthetic\n"
        "name dp_co tot_n min_n org_n tot_p min_p org_p sol_p h3a_p mehl_p bray_p description\n"
        "soilnut1 NOPE 6 3 3 3.5 0.4 0.15 0.25 1.2 0.85 0.85\n"
    )
    with pytest.raises(ParseError, match="expected float for 'dp_co'"):
        parse_nutrients_sol(p)
