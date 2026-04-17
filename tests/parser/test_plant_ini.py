"""Tests for ``swatplus_ai.parser.inputs.plant_ini``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.plant_ini import PlantIni, parse_plant_ini


def test_parse_minimal(minimal_project: Path) -> None:
    p = parse_plant_ini(minimal_project / "plant.ini")
    assert isinstance(p, PlantIni)
    assert len(p.communities) == 2

    frse = p.communities[0]
    assert frse.pcom_name == "frse_comm"
    assert frse.plt_cnt == 1
    assert frse.rot_yr_ini == 1
    assert len(frse.members) == 1
    m = frse.members[0]
    assert m.plt_name == "frse"
    assert m.lc_status is True
    assert m.lai_init == pytest.approx(2.0)
    assert m.bm_init == pytest.approx(50000.0)
    assert m.rsd_init == pytest.approx(10000.0)

    rot = p.communities[1]
    assert rot.pcom_name == "rotation_comm"
    assert rot.plt_cnt == 2
    assert len(rot.members) == 2
    assert [m.plt_name for m in rot.members] == ["corn", "soyb"]
    assert all(m.lc_status is False for m in rot.members)

    assert p.by_name("rotation_comm") is rot
    assert p.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    p = parse_plant_ini(uru_project / "plant.ini")
    assert len(p.communities) > 10
    # Every community's members list must match its declared plt_cnt.
    for c in p.communities:
        assert len(c.members) == c.plt_cnt
    # Community names used by URU landuse.lum should resolve.
    for expected in ("corn_comm", "frse_comm", "alfa_comm"):
        assert p.by_name(expected) is not None, f"missing {expected}"


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "plant.ini"
    p.write_text(
        "plant.ini: synthetic\n"
        "pcom_name plt_cnt rot_yr_ini plt_name lc_status lai_init bm_init "
        "phu_init plnt_pop yrs_init NOPE\n"
        "c1 1 1\n"
        "pl y 1 1 1 1 1 1\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_plant_ini(p)


def test_community_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "plant.ini"
    p.write_text(
        "plant.ini: synthetic\n"
        "pcom_name plt_cnt rot_yr_ini plt_name lc_status lai_init bm_init "
        "phu_init plnt_pop yrs_init rsd_init\n"
        "c1 1\n"  # missing rot_yr_ini
        "pl y 1 1 1 1 1 1\n"
    )
    with pytest.raises(ParseError, match="community row"):
        parse_plant_ini(p)


def test_member_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "plant.ini"
    p.write_text(
        "plant.ini: synthetic\n"
        "pcom_name plt_cnt rot_yr_ini plt_name lc_status lai_init bm_init "
        "phu_init plnt_pop yrs_init rsd_init\n"
        "c1 1 1\n"
        "pl y 1 1 1 1 1\n"  # only 7 member tokens
    )
    with pytest.raises(ParseError, match="plant member row"):
        parse_plant_ini(p)


def test_plt_cnt_exceeds_available_rows_raises(tmp_path: Path) -> None:
    p = tmp_path / "plant.ini"
    p.write_text(
        "plant.ini: synthetic\n"
        "pcom_name plt_cnt rot_yr_ini plt_name lc_status lai_init bm_init "
        "phu_init plnt_pop yrs_init rsd_init\n"
        "c1 3 1\n"
        "pl1 y 1 1 1 1 1 1\n"
        # only 1 member provided but plt_cnt claims 3
    )
    with pytest.raises(ParseError, match="plt_cnt=3"):
        parse_plant_ini(p)
