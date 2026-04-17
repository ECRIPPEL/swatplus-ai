"""Tests for ``swatplus_ai.parser.inputs.pesticide_pes``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.pesticide_pes import PesticidePes, parse_pesticide_pes


def test_parse_minimal(minimal_project: Path) -> None:
    p = parse_pesticide_pes(minimal_project / "pesticide.pes")
    assert isinstance(p, PesticidePes)
    assert len(p.rows) == 2
    first = p.by_name("245-tp")
    assert first is not None
    assert first.soil_ads == pytest.approx(2600.0)
    assert first.solub == pytest.approx(2.5)
    assert first.description == "Silvex_Amine"
    assert p.rows[1].description is None


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "pesticide.pes"
    p.write_text(
        "pesticide.pes: synthetic\n"
        "name NOPE frac_wash hl_foliage hl_soil solub aq_hlife aq_volat mol_wt "
        "aq_resus aq_settle ben_act_dep ben_bury ben_hlife description\n"
        "245-tp 2600 0.4 5 20 2.5 0.007 0.00001 0.1 0.002 0.5 0.3 0.002 0.05 desc\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_pesticide_pes(p)


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "pesticide.pes"
    p.write_text(
        "pesticide.pes: synthetic\n"
        "name soil_ads frac_wash hl_foliage hl_soil solub aq_hlife aq_volat mol_wt "
        "aq_resus aq_settle ben_act_dep ben_bury ben_hlife description\n"
        "245-tp 2600 0.4 5 20 2.5\n"
    )
    with pytest.raises(ParseError, match="expected at least 14 tokens"):
        parse_pesticide_pes(p)
