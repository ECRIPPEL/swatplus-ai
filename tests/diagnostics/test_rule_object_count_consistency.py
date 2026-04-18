"""Tests for rule ``setup.object_count_consistency``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _count_findings(project: TxtInOutProject) -> list[Finding]:
    return [
        f for f in _engine().run(project, stage="setup") if f.id == "setup.object_count_consistency"
    ]


def test_object_count_consistency_clean_project(
    clean_setup_project: TxtInOutProject,
) -> None:
    assert _count_findings(clean_setup_project) == []


def test_object_count_consistency_declared_too_low(
    clean_setup_project: TxtInOutProject,
) -> None:
    # hru_con has 2 rows; bump object_cnt.hru down to 0 to force a mismatch.
    assert clean_setup_project.object_cnt is not None
    fixed_cnt = clean_setup_project.object_cnt.model_copy(update={"hru": 0})
    project = clean_setup_project.model_copy(update={"object_cnt": fixed_cnt})
    findings = _count_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "error"
    assert f.location == "object.cnt"
    assert f.evidence == {"object": "hru", "declared": 0, "actual": 2}
    assert "0 hru objects" in f.message
    assert "has 2" in f.message


def test_object_count_consistency_declared_too_high(
    clean_setup_project: TxtInOutProject,
) -> None:
    assert clean_setup_project.object_cnt is not None
    fixed_cnt = clean_setup_project.object_cnt.model_copy(update={"cha": 5})
    project = clean_setup_project.model_copy(update={"object_cnt": fixed_cnt})
    findings = _count_findings(project)
    assert len(findings) == 1
    assert findings[0].evidence == {"object": "cha", "declared": 5, "actual": 1}


def test_object_count_consistency_skips_absent_con(
    clean_setup_project: TxtInOutProject,
) -> None:
    # Dropping chandeg_con removes it from the comparison entirely; the
    # other pairs remain consistent so no findings fire.
    assert clean_setup_project.object_cnt is not None
    fixed_cnt = clean_setup_project.object_cnt.model_copy(update={"cha": 99})
    project = clean_setup_project.model_copy(update={"chandeg_con": None, "object_cnt": fixed_cnt})
    assert _count_findings(project) == []


def test_object_count_consistency_reports_multiple_mismatches(
    clean_setup_project: TxtInOutProject,
) -> None:
    assert clean_setup_project.object_cnt is not None
    fixed_cnt = clean_setup_project.object_cnt.model_copy(update={"hru": 99, "aqu": 0})
    project = clean_setup_project.model_copy(update={"object_cnt": fixed_cnt})
    findings = _count_findings(project)
    objects = sorted(f.evidence["object"] for f in findings)
    assert objects == ["aqu", "hru"]
