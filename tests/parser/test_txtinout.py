"""Tests for ``swatplus_ai.parser.txtinout`` — the whole-project orchestrator."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from swatplus_ai.parser.txtinout import TxtInOutProject


def test_read_minimal(minimal_project: Path) -> None:
    p = TxtInOutProject.read(minimal_project)
    assert p.folder == minimal_project

    # Required files resolve to real parser models.
    assert p.time_sim.yrc_start > 0
    assert len(p.print_prt.objects) > 0
    assert p.codes_bsn.pet in {0, 1, 2, 3, 4}
    assert p.parameters_bsn.co2 > 0
    assert len(p.hru_data.rows) > 0
    assert len(p.topography_hyd.rows) > 0
    assert len(p.landuse_lum.rows) > 0
    assert len(p.plant_ini.communities) > 0
    assert len(p.soils_sol.soils) > 0
    assert len(p.management_sch.schedules) > 0
    assert len(p.weather_sta.rows) > 0
    assert len(p.weather_wgn.stations) > 0

    # Minimal fixture ships object.cnt; it should parse to a non-None model.
    assert p.object_cnt is not None
    assert p.object_cnt.obj > 0

    # Minimal fixture ships nutrients.sol; it should parse to a non-None model.
    assert p.nutrients_sol is not None
    assert len(p.nutrients_sol.rows) > 0

    # Minimal fixture ships the slice-4 parameter / operation / lookup DBs.
    assert p.fertilizer_frt is not None
    assert p.tillage_til is not None
    assert p.pesticide_pes is not None
    assert p.harv_ops is not None
    assert p.graze_ops is not None
    assert p.irr_ops is not None
    assert p.fire_ops is not None
    assert p.sweep_ops is not None
    assert p.chem_app_ops is not None
    assert p.cntable_lum is not None
    assert p.cons_practice_lum is not None
    assert p.ovn_table_lum is not None

    # Minimal fixture ships the slice-5 connectivity / topology files.
    assert p.hru_con is not None
    assert p.aquifer_con is not None
    assert p.chandeg_con is not None
    assert p.reservoir_con is not None
    assert p.rout_unit_con is not None
    assert p.ls_unit_def is not None
    assert p.ls_unit_ele is not None
    assert p.rout_unit_def is not None
    assert p.rout_unit_ele is not None
    assert p.rout_unit_rtu is not None
    assert p.aqu_catunit_ele is not None

    # Minimal fixture ships pcp.cli but not the other four observed files.
    assert p.pcp_cli is not None
    assert len(p.pcp_cli.filenames) > 0
    assert p.tmp_cli is None
    assert p.slr_cli is None
    assert p.hmd_cli is None
    assert p.wnd_cli is None


def test_read_uru(uru_project: Path) -> None:
    p = TxtInOutProject.read(uru_project)
    # URU is driven by real pcp + simulated (WGN) for everything else.
    assert p.pcp_cli is not None
    # Cross-file wiring sanity: hru-data.hru.lu_mgt must resolve in landuse.lum.
    for row in p.hru_data.rows:
        if row.lu_mgt is not None:
            assert (
                p.landuse_lum.by_name(row.lu_mgt) is not None
            ), f"hru-data references landuse {row.lu_mgt!r} missing from landuse.lum"
    # hru-data.hru.soil must resolve in soils.sol.
    for row in p.hru_data.rows:
        if row.soil is not None:
            assert p.soils_sol.by_name(row.soil) is not None


def test_read_missing_folder_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(NotADirectoryError, match="TxtInOut folder not found"):
        TxtInOutProject.read(missing)


def test_read_missing_required_file_raises(tmp_path: Path, minimal_project: Path) -> None:
    # Copy the minimal fixture and delete a required file to prove read() fails loudly.
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    (staging / "time.sim").unlink()
    with pytest.raises(FileNotFoundError):
        TxtInOutProject.read(staging)


def test_read_absent_optional_weather_cli_is_ok(tmp_path: Path, minimal_project: Path) -> None:
    # Copy the minimal fixture and remove pcp.cli to simulate a WGN-only project.
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    (staging / "pcp.cli").unlink()
    p = TxtInOutProject.read(staging)
    assert p.pcp_cli is None
    # Other required fields still load.
    assert len(p.weather_wgn.stations) > 0


def test_read_absent_object_cnt_is_ok(tmp_path: Path, minimal_project: Path) -> None:
    # object.cnt is a sanity-check inventory file; absence should not fail.
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    (staging / "object.cnt").unlink()
    p = TxtInOutProject.read(staging)
    assert p.object_cnt is None
    # Required fields still load.
    assert p.time_sim.yrc_start > 0


def test_read_absent_nutrients_sol_is_ok(tmp_path: Path, minimal_project: Path) -> None:
    # nutrients.sol is a soil-nutrient reference database; absence should not fail.
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    (staging / "nutrients.sol").unlink()
    p = TxtInOutProject.read(staging)
    assert p.nutrients_sol is None
    # Required fields still load.
    assert len(p.soils_sol.soils) > 0


def test_read_absent_slice5_topology_is_ok(tmp_path: Path, minimal_project: Path) -> None:
    # Projects may ship without connectivity files (e.g. pre-editor state).
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    for name in (
        "hru.con",
        "aquifer.con",
        "chandeg.con",
        "reservoir.con",
        "rout_unit.con",
        "ls_unit.def",
        "ls_unit.ele",
        "rout_unit.def",
        "rout_unit.ele",
        "rout_unit.rtu",
        "aqu_catunit.ele",
    ):
        (staging / name).unlink()
    p = TxtInOutProject.read(staging)
    assert p.hru_con is None
    assert p.aquifer_con is None
    assert p.chandeg_con is None
    assert p.reservoir_con is None
    assert p.rout_unit_con is None
    assert p.ls_unit_def is None
    assert p.ls_unit_ele is None
    assert p.rout_unit_def is None
    assert p.rout_unit_ele is None
    assert p.rout_unit_rtu is None
    assert p.aqu_catunit_ele is None
    # Required fields still load.
    assert len(p.hru_data.rows) > 0


def test_read_absent_slice4_dbs_is_ok(tmp_path: Path, minimal_project: Path) -> None:
    # Trimmed-down projects often omit unreferenced parameter / operation / lookup DBs.
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    for name in (
        "fertilizer.frt",
        "tillage.til",
        "pesticide.pes",
        "harv.ops",
        "graze.ops",
        "irr.ops",
        "fire.ops",
        "sweep.ops",
        "chem_app.ops",
        "cntable.lum",
        "cons_practice.lum",
        "ovn_table.lum",
    ):
        (staging / name).unlink()
    p = TxtInOutProject.read(staging)
    assert p.fertilizer_frt is None
    assert p.tillage_til is None
    assert p.pesticide_pes is None
    assert p.harv_ops is None
    assert p.graze_ops is None
    assert p.irr_ops is None
    assert p.fire_ops is None
    assert p.sweep_ops is None
    assert p.chem_app_ops is None
    assert p.cntable_lum is None
    assert p.cons_practice_lum is None
    assert p.ovn_table_lum is None
    # Required fields still load.
    assert len(p.hru_data.rows) > 0
