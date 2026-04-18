"""Tests for rule ``wb.et_precip_ratio``."""

from __future__ import annotations

import pandas as pd

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.outputs import OutputsNamespace
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="evaluation") if f.id == "wb.et_precip_ratio"]


def _project_with_wb(
    base: TxtInOutProject, precip: float, et: float, name: str = "basin"
) -> TxtInOutProject:
    df = pd.DataFrame([{"precip": precip, "et": et, "name": name}])
    outputs = OutputsNamespace(folder=base.folder, basin_wb_aa=df)
    return base.model_copy(update={"outputs": outputs})


def test_wb_et_precip_ratio_rule_loads_in_evaluation_stage() -> None:
    ids = {r.id for r in _engine().rules}
    assert "wb.et_precip_ratio" in ids


def test_wb_et_precip_ratio_in_range_emits_nothing(
    clean_setup_project: TxtInOutProject,
) -> None:
    # ratio = 0.5 → firmly inside [0.35, 0.95].
    project = _project_with_wb(clean_setup_project, precip=1000.0, et=500.0)
    assert _findings(project) == []


def test_wb_et_precip_ratio_below_threshold_warns(
    clean_setup_project: TxtInOutProject,
) -> None:
    # ratio = 0.2 → below 0.35 lower bound.
    project = _project_with_wb(clean_setup_project, precip=1000.0, et=200.0, name="basin_low")
    findings = _findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "warning"
    assert f.evidence["ratio"] == 0.2
    assert f.location == "basin_wb_aa.txt:basin_low"
    assert "below 0.35" in f.message


def test_wb_et_precip_ratio_above_threshold_warns(
    clean_setup_project: TxtInOutProject,
) -> None:
    # ratio = 0.98 → above 0.95 upper bound.
    project = _project_with_wb(clean_setup_project, precip=1000.0, et=980.0, name="basin_high")
    findings = _findings(project)
    assert len(findings) == 1
    assert findings[0].evidence["ratio"] == 0.98
    assert "above 0.95" in findings[0].message


def test_wb_et_precip_ratio_skipped_when_outputs_unset(
    clean_setup_project: TxtInOutProject,
) -> None:
    # OutputsNamespace with basin_wb_aa=None → the rule's `requires` gate
    # (outputs.basin_wb_aa) skips the check entirely.
    outputs = OutputsNamespace(folder=clean_setup_project.folder, basin_wb_aa=None)
    project = clean_setup_project.model_copy(update={"outputs": outputs})
    assert _findings(project) == []
