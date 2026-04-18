"""Tests for rule ``setup.warmup_ratio``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _warmup_findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="setup") if f.id == "setup.warmup_ratio"]


def test_warmup_ratio_clean_project(clean_setup_project: TxtInOutProject) -> None:
    # Baseline: yrc_end 2009, nyskip 2, span 10 → ratio 0.20 (between 0.10 and 0.33).
    assert _warmup_findings(clean_setup_project) == []


def test_warmup_ratio_too_low(clean_setup_project: TxtInOutProject) -> None:
    bad_print = clean_setup_project.print_prt.model_copy(update={"nyskip": 0})
    project = clean_setup_project.model_copy(update={"print_prt": bad_print})
    findings = _warmup_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "warning"
    assert f.location == "print.prt"
    assert f.evidence["nyskip"] == 0
    assert f.evidence["span"] == 10
    assert f.evidence["ratio"] == 0.0
    assert "low" in f.message


def test_warmup_ratio_too_high(clean_setup_project: TxtInOutProject) -> None:
    bad_print = clean_setup_project.print_prt.model_copy(update={"nyskip": 5})
    project = clean_setup_project.model_copy(update={"print_prt": bad_print})
    findings = _warmup_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "warning"
    assert f.evidence["nyskip"] == 5
    assert f.evidence["span"] == 10
    assert f.evidence["ratio"] == 0.5
    assert "wastefully high" in f.message


def test_warmup_ratio_skips_when_span_non_positive(
    clean_setup_project: TxtInOutProject,
) -> None:
    # span == 0 means sim_period_sanity owns the failure — warm-up check
    # bails out rather than dividing.
    bad_time = clean_setup_project.time_sim.model_copy(update={"yrc_start": 2005, "yrc_end": 2004})
    project = clean_setup_project.model_copy(update={"time_sim": bad_time})
    assert _warmup_findings(project) == []
