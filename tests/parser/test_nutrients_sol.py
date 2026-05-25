"""Tests for ``swatplus_ai.parser.inputs.nutrients_sol``.

Schema here mirrors the Fortran canonical ``soiltest_db`` type in
``soil_data_module.f90``. An earlier revision of this parser used an
outdated SWAT+ Toolbox baseline schema (``dp_co / tot_n / ...``) that
doesn't match any real project; that baseline was discarded in slice
7.3g after source consultation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.nutrients_sol import (
    NutrientsSol,
    parse_nutrients_sol,
)

_HEADER = (
    "name exp_co lab_p nitrate fr_hum_act hum_c_n hum_c_p inorgp "
    "watersol_p h3a_p mehlich_p bray_strong_p description"
)


def test_parse_minimal(minimal_project: Path) -> None:
    n = parse_nutrients_sol(minimal_project / "nutrients.sol")
    assert isinstance(n, NutrientsSol)
    assert len(n.rows) == 2
    first = n.rows[0]
    assert first.name == "soilnut1"
    assert first.exp_co == pytest.approx(0.001)
    assert first.lab_p == pytest.approx(5.0)
    assert first.nitrate == pytest.approx(7.0)
    assert first.hum_c_n == pytest.approx(10.0)
    assert first.bray_strong_p == pytest.approx(0.85)
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
        # Concentrations are non-negative for any real parameter set.
        assert row.lab_p >= 0
        assert row.nitrate >= 0
        assert row.inorgp >= 0


def test_missing_required_column_raises(tmp_path: Path) -> None:
    p = tmp_path / "nutrients.sol"
    p.write_text(
        "nutrients.sol: synthetic\n"
        "name exp_co lab_p nitrate fr_hum_act hum_c_n hum_c_p inorgp "
        "watersol_p h3a_p mehlich_p NOPE description\n"
        "soilnut1 0.001 5 7 0.02 10 80 0.5 0.15 0.25 1.2 0.85\n"
    )
    with pytest.raises(ParseError, match="missing expected column"):
        parse_nutrients_sol(p)


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "nutrients.sol"
    p.write_text(
        "nutrients.sol: synthetic\n"
        f"{_HEADER}\n"
        "soilnut1 0.001 5 7 0.02 10 80 0.5 0.15 0.25 1.2\n"  # 11 tokens, need >= 12
    )
    with pytest.raises(ParseError, match="expected at least 12 tokens"):
        parse_nutrients_sol(p)


def test_non_float_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "nutrients.sol"
    p.write_text(
        "nutrients.sol: synthetic\n"
        f"{_HEADER}\n"
        "soilnut1 NOPE 5 7 0.02 10 80 0.5 0.15 0.25 1.2 0.85\n"
    )
    with pytest.raises(ParseError, match="expected float for 'exp_co'"):
        parse_nutrients_sol(p)
