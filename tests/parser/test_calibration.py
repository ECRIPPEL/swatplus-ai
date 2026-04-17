"""Tests for slice-8 calibration / change parsers.

Covers the master calibratable-parameter registry (``cal_parms.cal``)
and the five soft-calibration control files (``codes.sft``,
``wb_parms.sft``, ``water_balance.sft``, ``plant_gro.sft``,
``plant_parms.sft``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.cal_parms_cal import parse_cal_parms_cal
from swatplus_ai.parser.inputs.codes_sft import parse_codes_sft
from swatplus_ai.parser.inputs.plant_gro_sft import parse_plant_gro_sft
from swatplus_ai.parser.inputs.plant_parms_sft import parse_plant_parms_sft
from swatplus_ai.parser.inputs.water_balance_sft import parse_water_balance_sft
from swatplus_ai.parser.inputs.wb_parms_sft import parse_wb_parms_sft

# --- cal_parms.cal -------------------------------------------------------


def test_parse_cal_parms_cal(minimal_project: Path) -> None:
    c = parse_cal_parms_cal(minimal_project / "cal_parms.cal")
    assert len(c.rows) == 3
    cn2 = c.by_name("cn2")
    assert cn2 is not None
    assert cn2.obj_typ == "hru"
    assert cn2.abs_min == pytest.approx(35.0)
    assert cn2.abs_max == pytest.approx(95.0)
    assert cn2.units is None
    alpha = c.by_name("alpha")
    assert alpha is not None
    assert alpha.units == "days"


def test_parse_cal_parms_cal_uru(uru_project: Path) -> None:
    c = parse_cal_parms_cal(uru_project / "cal_parms.cal")
    # URU ships 221 registry entries.
    assert len(c.rows) > 100
    # cn2 is the canonical runoff curve number parameter; must be present.
    assert c.by_name("cn2") is not None


def test_cal_parms_cal_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "cal_parms.cal"
    p.write_text(
        "cal_parms.cal: synthetic\n5\nname obj_typ abs_min abs_max units\ncn2 hru 35.0 95.0 null\n"
    )
    with pytest.raises(ParseError, match="declared 5 rows"):
        parse_cal_parms_cal(p)


def test_cal_parms_cal_token_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "cal_parms.cal"
    p.write_text("cal_parms.cal: synthetic\n1\nname obj_typ abs_min abs_max units\ncn2 hru 35.0\n")
    with pytest.raises(ParseError, match="expected 5 tokens"):
        parse_cal_parms_cal(p)


# --- codes.sft -----------------------------------------------------------


def test_parse_codes_sft(minimal_project: Path) -> None:
    c = parse_codes_sft(minimal_project / "codes.sft")
    assert c.hyd is True
    assert c.landscape is False
    assert c.plnt is False
    assert c.sed is False
    assert c.nut is True
    assert c.ch_sed is False
    assert c.ch_nut is False
    assert c.res is False


def test_parse_codes_sft_uru(uru_project: Path) -> None:
    c = parse_codes_sft(uru_project / "codes.sft")
    # URU is forward-sim only; all switches off.
    assert not any([c.hyd, c.landscape, c.plnt, c.sed, c.nut, c.ch_sed, c.ch_nut, c.res])


def test_codes_sft_bad_flag_raises(tmp_path: Path) -> None:
    p = tmp_path / "codes.sft"
    p.write_text(
        "codes.sft: synthetic\nhyd landscape plnt sed nut ch_sed ch_nut res\ny n n n y n n MAYBE\n"
    )
    with pytest.raises(ParseError, match="expected 'y' or 'n'"):
        parse_codes_sft(p)


# --- wb_parms.sft --------------------------------------------------------


def test_parse_wb_parms_sft(minimal_project: Path) -> None:
    w = parse_wb_parms_sft(minimal_project / "wb_parms.sft")
    assert len(w.rows) == 2
    cn2 = w.by_name("cn2")
    assert cn2 is not None
    assert cn2.chg_typ == "pctchg"
    assert cn2.neg == pytest.approx(-10.0)
    assert cn2.up == pytest.approx(95.0)


def test_parse_wb_parms_sft_uru(uru_project: Path) -> None:
    w = parse_wb_parms_sft(uru_project / "wb_parms.sft")
    assert len(w.rows) >= 1
    assert w.by_name("cn2") is not None


def test_wb_parms_sft_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "wb_parms.sft"
    p.write_text(
        "wb_parms.sft: synthetic\n3\nname chg_typ neg pos lo up\ncn2 pctchg -10.0 5.0 35.0 95.0\n"
    )
    with pytest.raises(ParseError, match="declared 3 rows"):
        parse_wb_parms_sft(p)


# --- water_balance.sft ---------------------------------------------------


def test_parse_water_balance_sft(minimal_project: Path) -> None:
    w = parse_water_balance_sft(minimal_project / "water_balance.sft")
    assert len(w.groups) == 1
    g = w.groups[0]
    assert g.name == "basin"
    assert len(g.targets) == 1
    t = g.targets[0]
    assert t.name == "basin"
    assert t.surq_rto == pytest.approx(18.1)
    assert t.perc_rto == pytest.approx(33.8)
    assert t.et_rto == pytest.approx(48.1)
    assert t.pet == pytest.approx(60.0)


def test_parse_water_balance_sft_uru(uru_project: Path) -> None:
    w = parse_water_balance_sft(uru_project / "water_balance.sft")
    assert len(w.groups) >= 1
    # URU ships one basin target row.
    assert any(len(g.targets) > 0 for g in w.groups)


# --- plant_gro.sft -------------------------------------------------------


def test_parse_plant_gro_sft(minimal_project: Path) -> None:
    p = parse_plant_gro_sft(minimal_project / "plant_gro.sft")
    assert len(p.groups) == 1
    g = p.groups[0]
    assert g.name == "basin"
    assert g.targets == ()


def test_parse_plant_gro_sft_uru(uru_project: Path) -> None:
    p = parse_plant_gro_sft(uru_project / "plant_gro.sft")
    assert len(p.groups) >= 1


# --- plant_parms.sft -----------------------------------------------------


def test_parse_plant_parms_sft(minimal_project: Path) -> None:
    p = parse_plant_parms_sft(minimal_project / "plant_parms.sft")
    assert len(p.groups) == 1
    g = p.groups[0]
    assert g.name == "basin"
    assert g.plants == 0
    assert g.parms == 0
    assert g.nspu == 0
    assert g.rows == ()


def test_parse_plant_parms_sft_uru(uru_project: Path) -> None:
    p = parse_plant_parms_sft(uru_project / "plant_parms.sft")
    assert len(p.groups) >= 1
