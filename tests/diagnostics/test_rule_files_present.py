"""Tests for rule ``setup.files_present``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def test_files_present_clean_project_no_findings(
    clean_setup_project: TxtInOutProject,
) -> None:
    findings = _engine().run(clean_setup_project, stage="setup")
    assert not [f for f in findings if f.id == "setup.files_present"]


def test_files_present_missing_object_cnt_fires(
    clean_setup_project: TxtInOutProject,
) -> None:
    # object_cnt is the only `_optional` field in the control-file set
    # that ``TxtInOutProject.read`` tolerates as ``None``; removing it
    # is the realistic failure mode the rule exists to catch.
    project = clean_setup_project.model_copy(update={"object_cnt": None})
    findings = [f for f in _engine().run(project, stage="setup") if f.id == "setup.files_present"]
    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "error"
    assert finding.location == "object.cnt"
    assert finding.evidence == {"file": "object.cnt"}
    assert "object.cnt" in finding.message
