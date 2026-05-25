"""Tests for rule ``setup.bsn.day_lag_max_as_float``.

The check consumes ``project.drifts`` (populated during parse) rather than
re-parsing the file, so drift injection via ``model_copy`` is how we
simulate a project that came from SWAT+ Editor < v3.1.0.
"""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.diagnostics.drift import DriftRecord
from swatplus_ai.parser.txtinout import TxtInOutProject

_DAY_LAG_DRIFT = DriftRecord(
    file="parameters.bsn",
    column="day_lag_max",
    observed="0.00000",
    expected_by_fortran="integer (basin_parms%day_lag_mx)",
    category="tool_bug",
    source_ref="https://github.com/swat-model/swatplus/blob/main/src/basin_module.f90",
    fixed_in_version="3.1.0",
)


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _findings(project: TxtInOutProject) -> list[Finding]:
    return [
        f for f in _engine().run(project, stage="setup") if f.id == "setup.bsn.day_lag_max_as_float"
    ]


def test_silent_when_no_drift_recorded(clean_setup_project: TxtInOutProject) -> None:
    # Clean project — no drift, no finding.
    assert clean_setup_project.drifts == ()
    assert _findings(clean_setup_project) == []


def test_warning_when_drift_present(clean_setup_project: TxtInOutProject) -> None:
    project = clean_setup_project.model_copy(update={"drifts": (_DAY_LAG_DRIFT,)})
    findings = _findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "warning"
    assert f.location == "parameters.bsn"
    assert f.evidence["observed"] == "0.00000"
    assert f.evidence["fixed_in_version"] == "3.1.0"
    assert "v3.1.0" in f.message


def test_silent_on_unrelated_drift(clean_setup_project: TxtInOutProject) -> None:
    other = DriftRecord(
        file="print.prt",
        column="some_other_col",
        observed="x",
        expected_by_fortran="y",
        category="tool_bug",
        source_ref="https://example/ref",
    )
    project = clean_setup_project.model_copy(update={"drifts": (other,)})
    assert _findings(project) == []
