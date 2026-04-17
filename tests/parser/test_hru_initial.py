"""Tests for slice-7 HRU initial / chemistry parsers.

Covers ``soil_plant.ini`` (HRU soil/plant initial-condition sets, wired
from ``hru-data.hru``) and ``om_water.ini`` (organic-matter / water
initial states referenced from the ``initial.{aqu,cha,res}`` files).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.om_water_ini import parse_om_water_ini
from swatplus_ai.parser.inputs.soil_plant_ini import parse_soil_plant_ini

# --- soil_plant.ini ------------------------------------------------------


def test_parse_soil_plant_ini(minimal_project: Path) -> None:
    s = parse_soil_plant_ini(minimal_project / "soil_plant.ini")
    r = s.by_name("soilplant1")
    assert r is not None
    assert r.sw_frac == pytest.approx(0.0)
    assert r.nutrients == "soilnut1"
    assert r.pest is None
    assert r.path is None
    assert r.hmet is None
    assert r.salt is None


def test_parse_soil_plant_ini_uru(uru_project: Path) -> None:
    s = parse_soil_plant_ini(uru_project / "soil_plant.ini")
    assert len(s.rows) >= 1
    # URU references soilplant1 from every hru-data row.
    assert s.by_name("soilplant1") is not None


def test_soil_plant_ini_token_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "soil_plant.ini"
    p.write_text(
        "soil_plant.ini: synthetic\n"
        "name sw_frac nutrients pest path hmet salt\n"
        "soilplant1 0.00000 soilnut1\n"
    )
    with pytest.raises(ParseError, match="expected 7 tokens"):
        parse_soil_plant_ini(p)


def test_soil_plant_ini_bad_sw_frac_raises(tmp_path: Path) -> None:
    p = tmp_path / "soil_plant.ini"
    p.write_text(
        "soil_plant.ini: synthetic\n"
        "name sw_frac nutrients pest path hmet salt\n"
        "soilplant1 NOT_A_FLOAT soilnut1 null null null null\n"
    )
    with pytest.raises(ParseError):
        parse_soil_plant_ini(p)


# --- om_water.ini --------------------------------------------------------


def test_parse_om_water_ini(minimal_project: Path) -> None:
    o = parse_om_water_ini(minimal_project / "om_water.ini")
    r = o.by_name("no_init")
    assert r is not None
    assert r.flo == pytest.approx(0.0)
    assert r.sed == pytest.approx(0.0)
    assert r.no3 == pytest.approx(0.0)
    assert r.dis_ox == pytest.approx(0.0)
    assert r.tmp == pytest.approx(0.0)
    assert r.c == pytest.approx(0.0)


def test_parse_om_water_ini_uru(uru_project: Path) -> None:
    o = parse_om_water_ini(uru_project / "om_water.ini")
    assert len(o.rows) >= 1
    # no_init is the universal "start empty" label referenced from initial.*.
    assert o.by_name("no_init") is not None


def test_om_water_ini_token_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "om_water.ini"
    p.write_text(
        "om_water.ini: synthetic\n"
        "name flo sed orgn sedp no3 solp chl_a nh3 no2 cbn_bod dis_ox "
        "san sil cla sag lag grv tmp c\n"
        "no_init 0.0 0.0 0.0\n"
    )
    with pytest.raises(ParseError, match="expected 20 tokens"):
        parse_om_water_ini(p)


def test_om_water_ini_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "om_water.ini"
    p.write_text(
        "om_water.ini: synthetic\n"
        "name WRONG sed orgn sedp no3 solp chl_a nh3 no2 cbn_bod dis_ox "
        "san sil cla sag lag grv tmp c\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_om_water_ini(p)
