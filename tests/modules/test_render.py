"""Tests for :func:`swatplus_ai.modules.setup_check.render_setup_check_result`.

Render tests assert on the printed *strings*, not on Rich's internal
object tree — the contract we care about is "modeler opens the terminal
and can read the report", so we grab the console output with
``Console(record=True)`` and inspect it.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.modules import SetupCheckResult, render_setup_check_result
from swatplus_ai.prompts import FormattedResponse, ProjectSummary
from swatplus_ai.prompts.formatter import Citation


def _result(
    *,
    findings: tuple[Finding, ...] = (),
    response: FormattedResponse | None = None,
) -> SetupCheckResult:
    summary = ProjectSummary(
        sim_start_year=2001,
        sim_end_year=2010,
        warmup_years=2,
        n_hrus=12,
        n_channels=3,
        n_aquifers=2,
        n_subbasins=3,
        pet_method=1,
        basin_area_km2=45.2,
    )
    return SetupCheckResult(
        project_path=Path("tests/fixtures/txtinout_minimal"),
        summary=summary,
        findings=findings,
        response=response,
        duration_ms=42,
    )


def _render(result: SetupCheckResult) -> str:
    console = Console(record=True, width=120)
    render_setup_check_result(result, console)
    return console.export_text()


def test_render_prints_project_path_in_summary_panel() -> None:
    out = _render(_result())
    assert "txtinout_minimal" in out


def test_render_shows_summary_fields() -> None:
    out = _render(_result())
    # A couple of known summary rows must be present so the reader can
    # orient themselves on the project at a glance.
    assert "sim_start_year" in out
    assert "2001" in out
    assert "pet_method" in out


def test_render_empty_findings_section_prints_zero_header() -> None:
    out = _render(_result())
    assert "Diagnostic findings (0)" in out


def test_render_findings_table_lists_each_finding() -> None:
    findings = (
        Finding(
            id="setup.files_present",
            severity="error",
            location=None,
            evidence={},
            rule_ref="setup.files_present",
            message="Required file missing: time.sim",
            references=("swatplus_io_spec",),
        ),
        Finding(
            id="setup.warmup_ratio",
            severity="warning",
            location=None,
            evidence={},
            rule_ref="setup.warmup_ratio",
            message="Warm-up is 50% of the simulation span",
            references=(),
        ),
    )
    out = _render(_result(findings=findings))
    assert "setup.files_present" in out
    assert "setup.warmup_ratio" in out
    assert "Required file missing" in out
    assert "Warm-up is 50%" in out
    assert "error" in out
    assert "warning" in out


def test_render_omits_llm_panel_when_response_none() -> None:
    out = _render(_result(response=None))
    assert "LLM response" not in out


def test_render_llm_panel_appears_when_response_present() -> None:
    response = FormattedResponse(
        text="See [doc:alpha] for detail.",
        citations=(Citation(handle="alpha", start=4, end=15, marker="[doc:alpha]"),),
        unknown_citations=(),
    )
    out = _render(_result(response=response))
    assert "LLM response" in out
    assert "[doc:alpha]" in out


def test_render_llm_panel_flags_unknown_citations() -> None:
    response = FormattedResponse(
        text="See [doc:unknown_handle] for detail.",
        citations=(
            Citation(
                handle="unknown_handle",
                start=4,
                end=24,
                marker="[doc:unknown_handle]",
            ),
        ),
        unknown_citations=("unknown_handle",),
    )
    out = _render(_result(response=response))
    # The unknown-handle call-out sits in the panel title so a skim
    # catches citations pointing outside the allowlist.
    assert "unknown_handle" in out
    assert "unknown" in out.lower()


def test_render_prints_duration_footer() -> None:
    out = _render(_result())
    assert "42 ms" in out
