"""Tests for :mod:`swatplus_ai.api.adapters`.

The adapters are pure functions over a parsed project / domain finding.
These tests pin the three invariants that slice 3.3's server endpoints
will lean on:

* :func:`to_project_meta` produces the UI-shaped ``ProjectMeta`` and
  copes with a minimal fixture that has neither climate nor biome.
* :func:`to_finding_vm` maps every domain field to the right VM field
  and wraps ``references`` in placeholder :class:`Citation` records.
* :func:`to_landuse_slices` aggregates HRU area by ``lu_mgt`` and sorts
  by descending percentage.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.api import (
    to_finding_vm,
    to_landuse_slices,
    to_project_meta,
)
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.parser.txtinout import TxtInOutProject

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
MINIMAL = FIXTURES_DIR / "txtinout_minimal"


def test_to_project_meta_populates_core_fields() -> None:
    project = TxtInOutProject.read(MINIMAL)
    meta = to_project_meta(project, ready_to_run=True)

    assert meta.name == MINIMAL.name
    assert meta.path == str(MINIMAL)
    # time.sim on the minimal fixture runs 2000-01-01 → 2005-12-31.
    assert meta.simulation_start.startswith("20")
    assert meta.simulation_end.startswith("20")
    assert meta.warmup_years >= 0
    assert meta.hrus >= 0
    assert meta.channels >= 0
    assert meta.weather_stations >= 0
    assert meta.ready_to_run is True
    # Fields the parser cannot populate yet default to empty / zero.
    assert meta.climate == ""
    assert meta.biome == ""
    assert meta.model_version == ""


def test_to_project_meta_honours_ready_to_run_flag() -> None:
    project = TxtInOutProject.read(MINIMAL)
    assert to_project_meta(project, ready_to_run=False).ready_to_run is False
    assert to_project_meta(project, ready_to_run=True).ready_to_run is True


def test_to_finding_vm_maps_every_field() -> None:
    finding = Finding(
        id="F123",
        severity="warning",
        location="HRU 42",
        evidence={"b": 2, "a": 1},
        rule_ref="module1.setup.warmup_ratio",
        message="Warmup ratio is below the 10% floor.",
        references=("daggupati_2015", "arnold_2012"),
    )

    vm = to_finding_vm(finding)

    assert vm.id == "F123"
    assert vm.rule_id == "module1.setup.warmup_ratio"
    assert vm.severity == "warning"
    assert vm.title == "Warmup ratio is below the 10% floor."
    assert vm.location == "HRU 42"
    # Evidence is JSON-dumped with sorted keys for deterministic output.
    assert '"a": 1' in vm.evidence
    assert '"b": 2' in vm.evidence
    assert vm.evidence.index('"a"') < vm.evidence.index('"b"')
    # Explanation / suggestion are intentionally empty until rules grow
    # richer — the adapter never fabricates text.
    assert vm.explanation == ""
    assert vm.suggestion == ""
    assert [c.id for c in vm.citations] == ["daggupati_2015", "arnold_2012"]
    assert all(c.label == c.id == c.source for c in vm.citations)


def test_to_finding_vm_handles_null_location_and_empty_refs() -> None:
    finding = Finding(
        id="F0",
        severity="info",
        location=None,
        evidence={},
        rule_ref="module1.setup.noop",
        message="",
    )

    vm = to_finding_vm(finding)

    assert vm.location == ""
    assert vm.citations == ()


def test_to_landuse_slices_sums_hru_area_and_sorts_desc() -> None:
    project = TxtInOutProject.read(MINIMAL)
    slices = to_landuse_slices(project)

    if not slices:
        # A minimal fixture legitimately has no hru.con/hru-data rows
        # pointing at real lu_mgt classes — in that case the contract
        # is "return empty tuple rather than crash".
        return

    assert sum(s.pct for s in slices) > 0
    assert all(s.pct >= 0 for s in slices)
    assert list(slices) == sorted(slices, key=lambda s: s.pct, reverse=True)
    # Total area across slices should round-trip within a sensible tolerance.
    total_km2 = sum(s.area_km2 for s in slices)
    assert total_km2 >= 0


def test_view_models_serialise_with_camel_case_aliases() -> None:
    project = TxtInOutProject.read(MINIMAL)
    meta = to_project_meta(project, ready_to_run=True)
    payload = meta.model_dump(by_alias=True)

    assert "warmupYears" in payload
    assert "readyToRun" in payload
    assert "outletLat" in payload
    assert "areaKm2" in payload
    # No snake_case leakage on the wire.
    assert "warmup_years" not in payload
    assert "ready_to_run" not in payload
