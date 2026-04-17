"""Tests for ``swatplus_ai.parser.inputs.soils_sol``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.soils_sol import SoilsSol, parse_soils_sol


def test_parse_minimal(minimal_project: Path) -> None:
    s = parse_soils_sol(minimal_project / "soils.sol")
    assert isinstance(s, SoilsSol)
    assert len(s.soils) == 2

    sandy = s.soils[0]
    assert sandy.name == "sandy_loam"
    assert sandy.nly == 2
    assert sandy.hyd_grp == "B"
    assert sandy.dp_tot == pytest.approx(1500.0)
    assert sandy.texture == "loam"
    assert len(sandy.layers) == 2
    top = sandy.layers[0]
    assert top.dp == pytest.approx(300.0)
    assert top.bd == pytest.approx(1.3)
    assert top.awc == pytest.approx(0.15)
    assert top.clay == pytest.approx(20.0)

    clay = s.soils[1]
    assert clay.name == "clay_soil"
    assert clay.nly == 1
    assert clay.hyd_grp == "D"
    assert len(clay.layers) == 1
    assert clay.layers[0].ph == pytest.approx(7.2)

    assert s.by_name("clay_soil") is clay
    assert s.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    s = parse_soils_sol(uru_project / "soils.sol")
    assert len(s.soils) > 10
    # Every soil's layer list must match its declared nly.
    for soil in s.soils:
        assert len(soil.layers) == soil.nly
        assert soil.hyd_grp in {"A", "B", "C", "D"}


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "soils.sol"
    p.write_text(
        "soils.sol: synthetic\n"
        "name nly hyd_grp dp_tot anion_excl perc_crk texture dp bd awc soil_k "
        "carbon clay silt sand rock alb usle_k ec caco3 NOPE\n"
        "s1 1 B 100 0.5 0.5 loam\n"
        "100 1.3 0.15 10 2 20 40 40 5 0.2 0.2 0 0 7\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_soils_sol(p)


def test_soil_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "soils.sol"
    p.write_text(
        "soils.sol: synthetic\n"
        "name nly hyd_grp dp_tot anion_excl perc_crk texture dp bd awc soil_k "
        "carbon clay silt sand rock alb usle_k ec caco3 ph\n"
        "s1 1 B 100 0.5 0.5\n"  # missing texture
        "100 1.3 0.15 10 2 20 40 40 5 0.2 0.2 0 0 7\n"
    )
    with pytest.raises(ParseError, match="soil row"):
        parse_soils_sol(p)


def test_layer_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "soils.sol"
    p.write_text(
        "soils.sol: synthetic\n"
        "name nly hyd_grp dp_tot anion_excl perc_crk texture dp bd awc soil_k "
        "carbon clay silt sand rock alb usle_k ec caco3 ph\n"
        "s1 1 B 100 0.5 0.5 loam\n"
        "100 1.3 0.15 10 2 20 40 40 5 0.2 0.2 0 0\n"  # 13 tokens, need 14
    )
    with pytest.raises(ParseError, match="soil layer row"):
        parse_soils_sol(p)


def test_nly_exceeds_available_rows_raises(tmp_path: Path) -> None:
    p = tmp_path / "soils.sol"
    p.write_text(
        "soils.sol: synthetic\n"
        "name nly hyd_grp dp_tot anion_excl perc_crk texture dp bd awc soil_k "
        "carbon clay silt sand rock alb usle_k ec caco3 ph\n"
        "s1 3 B 100 0.5 0.5 loam\n"
        "100 1.3 0.15 10 2 20 40 40 5 0.2 0.2 0 0 7\n"
        # only 1 layer provided but nly claims 3
    )
    with pytest.raises(ParseError, match="nly=3"):
        parse_soils_sol(p)
