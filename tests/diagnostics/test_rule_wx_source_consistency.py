"""Tests for rule ``wx.source_consistency``."""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.inputs.weather_cli import WeatherCli
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="setup") if f.id == "wx.source_consistency"]


def _pcp_index(path: Path, filenames: tuple[str, ...]) -> WeatherCli:
    return WeatherCli(source_path=path, title="pcp.cli synthetic", filenames=filenames)


def test_wx_source_consistency_clean_project(clean_setup_project: TxtInOutProject) -> None:
    # clean_setup_project drops pcp_cli, so the whole variable is skipped.
    assert _findings(clean_setup_project) == []


def test_wx_source_consistency_forward_gap(
    clean_setup_project: TxtInOutProject, tmp_path: Path
) -> None:
    # Station sta001 names "sta001.pcp"; a pcp.cli index missing that filename
    # should fire exactly one "not listed" finding.
    (tmp_path / "sta001.pcp").write_text("stub", encoding="utf-8")
    pcp = _pcp_index(tmp_path / "pcp.cli", filenames=("unrelated.pcp",))
    (tmp_path / "unrelated.pcp").write_text("stub", encoding="utf-8")
    project = clean_setup_project.model_copy(update={"folder": tmp_path, "pcp_cli": pcp})
    findings = _findings(project)
    forward = [f for f in findings if "not listed" in f.evidence.get("reason", "")]
    assert len(forward) == 1
    assert forward[0].evidence == {
        "reason": forward[0].evidence["reason"],
        "station": "sta001",
        "variable": "pcp",
        "filename": "sta001.pcp",
        "index": "pcp.cli",
    }
    assert forward[0].location == "weather-sta.cli:sta001:pcp"


def test_wx_source_consistency_reverse_gap_flags_missing_file(
    clean_setup_project: TxtInOutProject, tmp_path: Path
) -> None:
    # pcp.cli lists sta001.pcp, but only a stub for *that one* lives on disk;
    # also list sta999.pcp that isn't on disk to trigger the reverse finding.
    (tmp_path / "sta001.pcp").write_text("stub", encoding="utf-8")
    pcp = _pcp_index(tmp_path / "pcp.cli", filenames=("sta001.pcp", "sta999.pcp"))
    project = clean_setup_project.model_copy(update={"folder": tmp_path, "pcp_cli": pcp})
    findings = _findings(project)
    reverse = [f for f in findings if "not present" in f.evidence.get("reason", "")]
    assert len(reverse) == 1
    assert reverse[0].evidence["filename"] == "sta999.pcp"
    assert reverse[0].location == "pcp.cli:sta999.pcp"


def test_wx_source_consistency_skips_sim_and_null(
    clean_setup_project: TxtInOutProject, tmp_path: Path
) -> None:
    # sta001.pcp is observed, sta002 uses sim. A pcp.cli listing only
    # sta001.pcp (and the file is on disk) should fire nothing.
    (tmp_path / "sta001.pcp").write_text("stub", encoding="utf-8")
    pcp = _pcp_index(tmp_path / "pcp.cli", filenames=("sta001.pcp",))
    project = clean_setup_project.model_copy(update={"folder": tmp_path, "pcp_cli": pcp})
    assert _findings(project) == []
