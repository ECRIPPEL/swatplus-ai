"""Integration tests for slice 4.5.2 — parser and engine emission.

The core module (slice 4.5.1) provides :func:`swatplus_ai.telemetry.emit`
and is exercised in ``test_emit.py``. This file verifies the call sites:
:meth:`swatplus_ai.parser.txtinout.TxtInOutProject.read` emits
``file_parsed`` / ``parse_error`` and
:meth:`swatplus_ai.diagnostics.engine.DiagnosticEngine.run` emits
``rule_evaluated`` / ``finding_emitted``, with no behavioral change to
either method.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import swatplus_ai.telemetry as telemetry
from swatplus_ai.diagnostics import DiagnosticEngine
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.txtinout import TxtInOutProject
from swatplus_ai.telemetry.events import Event
from swatplus_ai.telemetry.sinks import InMemorySink, NullSink

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
MINIMAL = FIXTURES_DIR / "txtinout_minimal"

REQUIRED_FILENAMES = {
    "time.sim",
    "print.prt",
    "file.cio",
    "codes.bsn",
    "parameters.bsn",
    "hydrology.hyd",
    "topography.hyd",
    "hru-data.hru",
    "landuse.lum",
    "plant.ini",
    "soils.sol",
    "management.sch",
    "weather-sta.cli",
    "weather-wgn.cli",
}


def _file_parsed_names(events: list[Event]) -> set[str]:
    return {e.fields["filename"] for e in events if e.event_type == "file_parsed"}


def _rule_events(events: list[Event], kind: str) -> list[Event]:
    return [e for e in events if e.event_type == kind]


def test_parser_emits_file_parsed_for_required_files(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    TxtInOutProject.read(MINIMAL)
    emitted = _file_parsed_names(sink.events)
    missing = REQUIRED_FILENAMES - emitted
    assert not missing, f"Required files not emitted: {missing}"


def test_parser_file_parsed_event_shape(enable_telemetry: None) -> None:
    sink = InMemorySink()
    telemetry.configure(sink)
    TxtInOutProject.read(MINIMAL)
    time_sim_events = [
        e
        for e in sink.events
        if e.event_type == "file_parsed" and e.fields["filename"] == "time.sim"
    ]
    assert len(time_sim_events) == 1
    fields = time_sim_events[0].fields
    # time.sim is a single-row control file → no row count to report.
    assert fields["rows"] is None
    assert isinstance(fields["duration_ms"], int)
    assert fields["duration_ms"] >= 0
    # hru-data.hru has a rows tuple → non-negative int.
    hru_fields = next(
        e.fields
        for e in sink.events
        if e.event_type == "file_parsed" and e.fields["filename"] == "hru-data.hru"
    )
    assert isinstance(hru_fields["rows"], int)
    assert hru_fields["rows"] >= 1


def test_parser_optional_absent_emits_nothing(tmp_path: Path, enable_telemetry: None) -> None:
    scrubbed = tmp_path / "project"
    shutil.copytree(MINIMAL, scrubbed)
    # Remove one optional file; its absence must not emit any event.
    (scrubbed / "pcp.cli").unlink()
    sink = InMemorySink()
    telemetry.configure(sink)
    TxtInOutProject.read(scrubbed)
    names_by_type = {
        (e.event_type, e.fields.get("filename"))
        for e in sink.events
        if e.event_type in {"file_parsed", "parse_error"}
    }
    assert ("file_parsed", "pcp.cli") not in names_by_type
    assert ("parse_error", "pcp.cli") not in names_by_type


def test_parser_error_path_emits_parse_error(tmp_path: Path, enable_telemetry: None) -> None:
    scrubbed = tmp_path / "project"
    shutil.copytree(MINIMAL, scrubbed)
    # Truncate time.sim to just the title — the header line is now missing.
    (scrubbed / "time.sim").write_text("oh no a broken file\n", encoding="utf-8")
    sink = InMemorySink()
    telemetry.configure(sink)
    with pytest.raises(ParseError):
        TxtInOutProject.read(scrubbed)
    parse_errors = _rule_events(sink.events, "parse_error")
    assert len(parse_errors) == 1
    fields = parse_errors[0].fields
    assert fields["filename"] == "time.sim"
    assert fields["exception"] == "ParseError"
    # ParseError carries a 1-based line number; we forward it under "line".
    assert "line" in fields
    assert isinstance(fields["line"], int)


def test_engine_emits_one_rule_evaluated_per_setup_rule(
    enable_telemetry: None,
) -> None:
    project = TxtInOutProject.read(MINIMAL)
    engine = DiagnosticEngine.from_builtin_rules()
    setup_rule_ids = {r.id for r in engine.rules if "setup" in r.stage}

    sink = InMemorySink()
    telemetry.configure(sink)
    findings = engine.run(project, stage="setup")

    rule_events = _rule_events(sink.events, "rule_evaluated")
    emitted_ids = [e.fields["rule_id"] for e in rule_events]
    assert set(emitted_ids) == setup_rule_ids
    assert len(emitted_ids) == len(setup_rule_ids)
    # Engine <-> sink accounting: every finding returned is also logged.
    total_finding_count = sum(
        int(e.fields["finding_count"]) for e in rule_events if not e.fields.get("skipped")
    )
    assert total_finding_count == len(findings)
    # And one finding_emitted per returned finding.
    assert len(_rule_events(sink.events, "finding_emitted")) == len(findings)


def test_engine_emits_skipped_when_requires_unsatisfied(
    enable_telemetry: None,
) -> None:
    project = TxtInOutProject.read(MINIMAL)
    # Force outputs.basin_wb_aa to None so wb.et_precip_ratio's requires fails.
    empty_outputs = project.outputs.model_copy(update={"basin_wb_aa": None})
    project_no_wb = project.model_copy(update={"outputs": empty_outputs})

    engine = DiagnosticEngine.from_builtin_rules()
    sink = InMemorySink()
    telemetry.configure(sink)
    engine.run(project_no_wb, stage="evaluation")

    rule_events = _rule_events(sink.events, "rule_evaluated")
    wb_events = [e for e in rule_events if e.fields["rule_id"] == "wb.et_precip_ratio"]
    assert len(wb_events) == 1
    fields = wb_events[0].fields
    assert fields["skipped"] is True
    assert fields["finding_count"] == 0
    assert fields["duration_ms"] == 0


def test_engine_ordering_findings_before_rule_evaluated(
    enable_telemetry: None,
) -> None:
    # Use a synthetic rule that yields exactly two findings so we can pin
    # the emission order: N finding_emitted → one rule_evaluated.
    from swatplus_ai.diagnostics import Rule, register_check
    from swatplus_ai.diagnostics.registry import _CHECKS, CheckResult

    check_name = "_test_two_findings"
    try:

        @register_check(check_name)
        def _two_findings(_project: TxtInOutProject) -> list[CheckResult]:
            return [
                CheckResult(location="loc1", evidence={}),
                CheckResult(location="loc2", evidence={}),
            ]

        rule = Rule(
            id="test.two_findings",
            severity="warning",
            stage=("setup",),
            requires=(),
            check=check_name,
            message="synthetic",
        )
        engine = DiagnosticEngine((rule,))
        # Drain parser emissions to a null sink first so only engine
        # events land in the in-memory sink we assert on.
        telemetry.configure(NullSink())
        project = TxtInOutProject.read(MINIMAL)
        sink = InMemorySink()
        telemetry.configure(sink)
        findings = engine.run(project, stage="setup")
        assert len(findings) == 2

        # Sequence should be: finding_emitted, finding_emitted, rule_evaluated.
        types = [e.event_type for e in sink.events]
        assert types == ["finding_emitted", "finding_emitted", "rule_evaluated"]
        assert sink.events[-1].fields["finding_count"] == 2
    finally:
        _CHECKS.pop(check_name, None)


def test_instrumentation_noop_when_telemetry_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # SWATPLUS_AI_NO_LOG=1 short-circuits emit() before any Event is built.
    monkeypatch.setenv("SWATPLUS_AI_NO_LOG", "1")
    sink = InMemorySink()
    telemetry.configure(sink)
    project = TxtInOutProject.read(MINIMAL)
    engine = DiagnosticEngine.from_builtin_rules()
    engine.run(project, stage="setup")
    assert sink.events == []


def test_instrumentation_contract_no_behavioral_change(
    enable_telemetry: None,
) -> None:
    # With and without a sink attached, run() must produce the same list.
    project = TxtInOutProject.read(MINIMAL)
    engine = DiagnosticEngine.from_builtin_rules()

    telemetry.configure(NullSink())
    baseline = engine.run(project, stage="setup")

    telemetry.configure(InMemorySink())
    instrumented = engine.run(project, stage="setup")

    assert [f.id for f in baseline] == [f.id for f in instrumented]
    assert [f.severity for f in baseline] == [f.severity for f in instrumented]
    assert [f.message for f in baseline] == [f.message for f in instrumented]


def test_parser_file_parsed_emits_for_output_file(enable_telemetry: None) -> None:
    # Outputs-namespace instrumentation: an annual-average .txt file gets
    # a file_parsed event with rows = len(df).
    sink = InMemorySink()
    telemetry.configure(sink)
    TxtInOutProject.read(MINIMAL)
    output_events = [
        e
        for e in sink.events
        if e.event_type == "file_parsed" and e.fields["filename"] == "basin_wb_aa.txt"
    ]
    assert len(output_events) == 1
    fields = output_events[0].fields
    assert isinstance(fields["rows"], int)
    assert fields["rows"] >= 1


def test_engine_finding_severity_uses_effective_value(enable_telemetry: None) -> None:
    # A CheckResult with an explicit severity override should propagate
    # to the finding_emitted event (not the rule's declared default).
    from swatplus_ai.diagnostics import Rule, register_check
    from swatplus_ai.diagnostics.registry import _CHECKS, CheckResult

    check_name = "_test_severity_override"
    try:

        @register_check(check_name)
        def _override(_project: TxtInOutProject) -> CheckResult:
            return CheckResult(location="x", evidence={}, severity="error")

        rule = Rule(
            id="test.severity_override",
            severity="info",
            stage=("setup",),
            requires=(),
            check=check_name,
            message="synthetic",
        )
        engine = DiagnosticEngine((rule,))
        project = TxtInOutProject.read(MINIMAL)

        sink = InMemorySink()
        telemetry.configure(sink)
        findings = engine.run(project, stage="setup")
        assert findings[0].severity == "error"

        finding_events = _rule_events(sink.events, "finding_emitted")
        assert len(finding_events) == 1
        assert finding_events[0].fields["severity"] == "error"
    finally:
        _CHECKS.pop(check_name, None)


def test_engine_non_matching_stage_emits_nothing(enable_telemetry: None) -> None:
    # Rules whose stage doesn't include the run's stage are silent —
    # no rule_evaluated event for them.
    project = TxtInOutProject.read(MINIMAL)
    engine = DiagnosticEngine.from_builtin_rules()
    calibration_rules = [r for r in engine.rules if "calibration" in r.stage]
    # The current bundled rule set has no calibration-stage rules, so a
    # calibration run should produce zero rule_evaluated events.
    assert calibration_rules == []

    sink = InMemorySink()
    telemetry.configure(sink)
    engine.run(project, stage="calibration")
    assert _rule_events(sink.events, "rule_evaluated") == []


def test_engine_finding_list_identity_unchanged(enable_telemetry: None) -> None:
    # A looser regression guard: running twice with an in-memory sink must
    # return Finding objects equal in content (Finding is a frozen
    # pydantic model, so equality is structural).
    project = TxtInOutProject.read(MINIMAL)
    engine = DiagnosticEngine.from_builtin_rules()

    telemetry.configure(InMemorySink())
    first: list[Finding] = engine.run(project, stage="setup")

    telemetry.configure(InMemorySink())
    second: list[Finding] = engine.run(project, stage="setup")

    assert first == second
