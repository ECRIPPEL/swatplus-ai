"""Tests for rule ``setup.sim_period_sanity``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _period_findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="setup") if f.id == "setup.sim_period_sanity"]


def test_sim_period_sanity_clean_project(clean_setup_project: TxtInOutProject) -> None:
    assert _period_findings(clean_setup_project) == []


def test_sim_period_sanity_inverted_year_range(
    clean_setup_project: TxtInOutProject,
) -> None:
    bad_time = clean_setup_project.time_sim.model_copy(update={"yrc_start": 2005, "yrc_end": 2000})
    project = clean_setup_project.model_copy(update={"time_sim": bad_time})
    findings = _period_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "error"
    assert f.location == "time.sim"
    assert f.evidence["yrc_start"] == 2005
    assert f.evidence["yrc_end"] == 2000
    assert "inverted" in f.message


def test_sim_period_sanity_single_year_zero_length(
    clean_setup_project: TxtInOutProject,
) -> None:
    bad_time = clean_setup_project.time_sim.model_copy(
        update={
            "yrc_start": 2005,
            "yrc_end": 2005,
            "day_start": 200,
            "day_end": 100,
        }
    )
    project = clean_setup_project.model_copy(update={"time_sim": bad_time})
    findings = _period_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "error"
    assert f.evidence["day_start"] == 200
    assert f.evidence["day_end"] == 100
    assert "ends at or before start" in f.message


def test_sim_period_sanity_short_span_warning(
    clean_setup_project: TxtInOutProject,
) -> None:
    bad_time = clean_setup_project.time_sim.model_copy(update={"yrc_start": 2005, "yrc_end": 2005})
    # Also bump nyskip to 0 so the warm-up rule doesn't also fire when we
    # later assert *only* the sim-period finding — but here we just
    # filter on rule id anyway.
    bad_print = clean_setup_project.print_prt.model_copy(update={"nyskip": 0})
    project = clean_setup_project.model_copy(update={"time_sim": bad_time, "print_prt": bad_print})
    findings = _period_findings(project)
    assert len(findings) == 1
    f = findings[0]
    # Severity demoted from the rule default (error) via CheckResult override.
    assert f.severity == "warning"
    assert f.evidence["span"] == 1
    assert "too short" in f.message
