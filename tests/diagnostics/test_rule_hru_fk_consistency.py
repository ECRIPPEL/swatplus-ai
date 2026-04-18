"""Tests for rule ``hru.fk_consistency``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _fk_findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="setup") if f.id == "hru.fk_consistency"]


def test_fk_consistency_clean_project(clean_setup_project: TxtInOutProject) -> None:
    assert _fk_findings(clean_setup_project) == []


def test_fk_consistency_flags_broken_soil(clean_setup_project: TxtInOutProject) -> None:
    rows = clean_setup_project.hru_data.rows
    broken = rows[0].model_copy(update={"soil": "nonexistent_soil"})
    fixed_hru = clean_setup_project.hru_data.model_copy(update={"rows": (broken, rows[1])})
    project = clean_setup_project.model_copy(update={"hru_data": fixed_hru})
    findings = _fk_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "error"
    assert f.location == f"hru-data.hru:row={rows[0].id}"
    assert f.evidence == {
        "row_id": rows[0].id,
        "field": "soil",
        "value": "nonexistent_soil",
        "target": "soils.sol",
    }
    assert "nonexistent_soil" in f.message
    assert "soils.sol" in f.message


def test_fk_consistency_flags_broken_lu_mgt(clean_setup_project: TxtInOutProject) -> None:
    rows = clean_setup_project.hru_data.rows
    broken = rows[1].model_copy(update={"lu_mgt": "typo_lum"})
    fixed_hru = clean_setup_project.hru_data.model_copy(update={"rows": (rows[0], broken)})
    project = clean_setup_project.model_copy(update={"hru_data": fixed_hru})
    findings = _fk_findings(project)
    assert len(findings) == 1
    assert findings[0].evidence["field"] == "lu_mgt"
    assert findings[0].evidence["target"] == "landuse.lum"


def test_fk_consistency_skips_null_values(clean_setup_project: TxtInOutProject) -> None:
    # A null FK slot is a legal "unused" marker, not a broken reference.
    rows = clean_setup_project.hru_data.rows
    nulled = rows[0].model_copy(update={"lu_mgt": None, "topo": None})
    fixed_hru = clean_setup_project.hru_data.model_copy(update={"rows": (nulled, rows[1])})
    project = clean_setup_project.model_copy(update={"hru_data": fixed_hru})
    assert _fk_findings(project) == []


def test_fk_consistency_reports_one_finding_per_broken_fk(
    clean_setup_project: TxtInOutProject,
) -> None:
    # Break three FKs on one row; expect three findings, all keyed to that row.
    rows = clean_setup_project.hru_data.rows
    broken = rows[0].model_copy(
        update={"soil": "bad_soil", "topo": "bad_topo", "hydro": "bad_hydro"}
    )
    fixed_hru = clean_setup_project.hru_data.model_copy(update={"rows": (broken, rows[1])})
    project = clean_setup_project.model_copy(update={"hru_data": fixed_hru})
    findings = _fk_findings(project)
    fields = sorted(f.evidence["field"] for f in findings)
    assert fields == ["hydro", "soil", "topo"]
    assert {f.location for f in findings} == {f"hru-data.hru:row={rows[0].id}"}
