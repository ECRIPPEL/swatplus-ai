"""Tests for slice-6 routing-body parsers.

Covers the physical and initial-condition parameter files for aquifers
(``aquifer.aqu``, ``initial.aqu``), channels (``channel-lte.cha``,
``hyd-sed-lte.cha``, ``nutrients.cha``, ``initial.cha``), reservoirs
(``reservoir.res``, ``hydrology.res``, ``nutrients.res``,
``sediment.res``, ``initial.res``), and wetlands (``wetland.wet``,
``hydrology.wet``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.aquifer_aqu import parse_aquifer_aqu
from swatplus_ai.parser.inputs.channel_lte_cha import parse_channel_lte_cha
from swatplus_ai.parser.inputs.hyd_sed_lte_cha import parse_hyd_sed_lte_cha
from swatplus_ai.parser.inputs.hydrology_res import parse_hydrology_res
from swatplus_ai.parser.inputs.hydrology_wet import parse_hydrology_wet
from swatplus_ai.parser.inputs.initial_any import parse_initial_any
from swatplus_ai.parser.inputs.nutrients_cha import parse_nutrients_cha
from swatplus_ai.parser.inputs.nutrients_res import parse_nutrients_res
from swatplus_ai.parser.inputs.reservoir_res import parse_reservoir_res
from swatplus_ai.parser.inputs.sediment_res import parse_sediment_res
from swatplus_ai.parser.inputs.wetland_wet import parse_wetland_wet

# --- initial.{aqu,cha,res} shared parser ---------------------------------


def test_parse_initial_aqu(minimal_project: Path) -> None:
    i = parse_initial_any(minimal_project / "initial.aqu")
    r = i.by_name("initaqu1")
    assert r is not None
    assert r.org_min == "no_init"
    assert r.pest is None
    assert r.path is None
    assert r.hmet is None
    assert r.salt is None


def test_parse_initial_cha(minimal_project: Path) -> None:
    i = parse_initial_any(minimal_project / "initial.cha")
    assert i.by_name("initcha1") is not None


def test_parse_initial_res(minimal_project: Path) -> None:
    i = parse_initial_any(minimal_project / "initial.res")
    assert i.by_name("initres1") is not None


# --- aquifer.aqu ---------------------------------------------------------


def test_parse_aquifer_aqu(minimal_project: Path) -> None:
    a = parse_aquifer_aqu(minimal_project / "aquifer.aqu")
    r = a.by_name("aqu001")
    assert r is not None
    assert r.init == "initaqu1"
    assert r.gw_flo == pytest.approx(0.05)
    assert r.dep_bot == pytest.approx(10.0)
    assert r.spec_yld == pytest.approx(0.05)


def test_parse_aquifer_aqu_uru(uru_project: Path) -> None:
    a = parse_aquifer_aqu(uru_project / "aquifer.aqu")
    assert len(a.rows) > 10
    assert all(r.init for r in a.rows)


def test_aquifer_aqu_token_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "aquifer.aqu"
    p.write_text(
        "aquifer.aqu: synthetic\n"
        "id name init gw_flo dep_bot dep_wt no3_n sol_p carbon flo_dist bf_max "
        "alpha_bf revap rchg_dp spec_yld hl_no3n flo_min revap_min\n"
        "1 aqu001 initaqu1 0.05 10.0\n"
    )
    with pytest.raises(ParseError, match="expected 18 tokens"):
        parse_aquifer_aqu(p)


# --- channel-lte.cha -----------------------------------------------------


def test_parse_channel_lte_cha(minimal_project: Path) -> None:
    c = parse_channel_lte_cha(minimal_project / "channel-lte.cha")
    r = c.by_name("cha001")
    assert r is not None
    assert r.cha_ini == "initcha1"
    assert r.cha_hyd == "hydcha001"
    assert r.cha_sed is None
    assert r.cha_nut == "nutcha1"


def test_parse_channel_lte_cha_uru(uru_project: Path) -> None:
    c = parse_channel_lte_cha(uru_project / "channel-lte.cha")
    assert len(c.rows) > 100


# --- hyd-sed-lte.cha -----------------------------------------------------


def test_parse_hyd_sed_lte_cha(minimal_project: Path) -> None:
    h = parse_hyd_sed_lte_cha(minimal_project / "hyd-sed-lte.cha")
    r = h.by_name("hydcha001")
    assert r is not None
    assert r.order == 1
    assert r.wd == pytest.approx(100.0)
    assert r.mann == pytest.approx(0.05)
    assert r.description is None


def test_parse_hyd_sed_lte_cha_uru(uru_project: Path) -> None:
    h = parse_hyd_sed_lte_cha(uru_project / "hyd-sed-lte.cha")
    assert len(h.rows) > 100


# --- nutrients.cha -------------------------------------------------------


def test_parse_nutrients_cha(minimal_project: Path) -> None:
    n = parse_nutrients_cha(minimal_project / "nutrients.cha")
    r = n.by_name("nutcha1")
    assert r is not None
    assert r.alg_stl == pytest.approx(1.0)
    assert r.q2e_lt == pytest.approx(2.0)
    assert r.q2e_alg == pytest.approx(2.0)
    assert r.nh3_pref == pytest.approx(0.5)


def test_parse_nutrients_cha_uru(uru_project: Path) -> None:
    n = parse_nutrients_cha(uru_project / "nutrients.cha")
    assert len(n.rows) >= 1


# --- reservoir.res -------------------------------------------------------


def test_parse_reservoir_res(minimal_project: Path) -> None:
    r = parse_reservoir_res(minimal_project / "reservoir.res")
    row = r.by_name("res001")
    assert row is not None
    assert row.init == "initres1"
    assert row.hyd == "hydres1"
    assert row.nut == "nutres1"


def test_parse_reservoir_res_uru(uru_project: Path) -> None:
    r = parse_reservoir_res(uru_project / "reservoir.res")
    assert len(r.rows) >= 1


# --- hydrology.res -------------------------------------------------------


def test_parse_hydrology_res(minimal_project: Path) -> None:
    h = parse_hydrology_res(minimal_project / "hydrology.res")
    r = h.by_name("hydres1")
    assert r is not None
    assert r.yr_op == 1
    assert r.mon_op == 1
    assert r.vol_ps == pytest.approx(50000.0)
    assert r.evap_co == pytest.approx(0.6)


def test_parse_hydrology_res_uru(uru_project: Path) -> None:
    h = parse_hydrology_res(uru_project / "hydrology.res")
    assert len(h.rows) >= 1


# --- nutrients.res -------------------------------------------------------


def test_parse_nutrients_res(minimal_project: Path) -> None:
    n = parse_nutrients_res(minimal_project / "nutrients.res")
    r = n.by_name("nutres1")
    assert r is not None
    assert r.mid_start == 5
    assert r.mid_end == 10
    assert r.n_min_stl == pytest.approx(0.1)


def test_parse_nutrients_res_uru(uru_project: Path) -> None:
    n = parse_nutrients_res(uru_project / "nutrients.res")
    assert len(n.rows) >= 1


# --- sediment.res --------------------------------------------------------


def test_parse_sediment_res(minimal_project: Path) -> None:
    s = parse_sediment_res(minimal_project / "sediment.res")
    r = s.by_name("sedres1")
    assert r is not None
    assert r.sed_amt == pytest.approx(1.0)
    assert r.d50 == pytest.approx(10.0)


def test_parse_sediment_res_uru(uru_project: Path) -> None:
    s = parse_sediment_res(uru_project / "sediment.res")
    assert len(s.rows) >= 1


# --- wetland.wet ---------------------------------------------------------


def test_parse_wetland_wet(minimal_project: Path) -> None:
    w = parse_wetland_wet(minimal_project / "wetland.wet")
    r = w.by_name("wet001")
    assert r is not None
    assert r.hyd == "hydwet001"
    assert r.rel == "wetland"


def test_parse_wetland_wet_uru(uru_project: Path) -> None:
    w = parse_wetland_wet(uru_project / "wetland.wet")
    assert len(w.rows) > 10


# --- hydrology.wet -------------------------------------------------------


def test_parse_hydrology_wet(minimal_project: Path) -> None:
    h = parse_hydrology_wet(minimal_project / "hydrology.wet")
    r = h.by_name("hydwet001")
    assert r is not None
    assert r.hru_frac == pytest.approx(0.5)
    assert r.evap == pytest.approx(0.7)


def test_parse_hydrology_wet_uru(uru_project: Path) -> None:
    h = parse_hydrology_wet(uru_project / "hydrology.wet")
    assert len(h.rows) > 10


# --- error paths ---------------------------------------------------------


def test_initial_any_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "initial.aqu"
    p.write_text(
        "initial.aqu: synthetic\n"
        "name NOPE pest path hmet salt description\n"
        "initaqu1 no_init null null null null null\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_initial_any(p)


def test_channel_lte_cha_token_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "channel-lte.cha"
    p.write_text(
        "channel-lte.cha: synthetic\n"
        "id name cha_ini cha_hyd cha_sed cha_nut\n"
        "1 cha001 initcha1 hydcha001 null\n"
    )
    with pytest.raises(ParseError, match="expected 6 tokens"):
        parse_channel_lte_cha(p)


def test_hydrology_res_wrong_token_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "hydrology.res"
    p.write_text(
        "hydrology.res: synthetic\n"
        "name yr_op mon_op area_ps vol_ps area_es vol_es k evap_co shp_co1 shp_co2\n"
        "hydres1 1 1 1000.0\n"
    )
    with pytest.raises(ParseError, match="expected 11 tokens"):
        parse_hydrology_res(p)
