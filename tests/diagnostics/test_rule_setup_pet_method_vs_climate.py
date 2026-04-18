"""Tests for rule ``setup.pet_method_vs_climate``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _findings(project: TxtInOutProject) -> list[Finding]:
    return [
        f for f in _engine().run(project, stage="setup") if f.id == "setup.pet_method_vs_climate"
    ]


def test_pet_hargreaves_emits_nothing(clean_setup_project: TxtInOutProject) -> None:
    # clean_setup_project pins pet=3 (Hargreaves) specifically so every
    # rule except this one stays quiet. The rule itself should also be
    # vacuous because Hargreaves needs only temperature.
    assert _findings(clean_setup_project) == []


def test_pet_penman_monteith_all_sim_flags_three_vars(
    clean_setup_project: TxtInOutProject,
) -> None:
    fixed = clean_setup_project.codes_bsn.model_copy(update={"pet": 1})
    project = clean_setup_project.model_copy(update={"codes_bsn": fixed})
    findings = _findings(project)
    vars_flagged = sorted(f.evidence["variable"] for f in findings)
    assert vars_flagged == ["hmd", "slr", "wnd"]
    assert {f.severity for f in findings} == {"warning"}


def test_pet_priestley_taylor_all_sim_flags_two_vars(
    clean_setup_project: TxtInOutProject,
) -> None:
    fixed = clean_setup_project.codes_bsn.model_copy(update={"pet": 2})
    project = clean_setup_project.model_copy(update={"codes_bsn": fixed})
    findings = _findings(project)
    vars_flagged = sorted(f.evidence["variable"] for f in findings)
    assert vars_flagged == ["hmd", "slr"]


def test_pet_penman_monteith_with_one_observed_station_silences_variable(
    clean_setup_project: TxtInOutProject,
) -> None:
    # Observed slr on even one station silences the slr finding; hmd and
    # wnd are still all-sim so they remain flagged.
    sta = clean_setup_project.weather_sta
    rows = (sta.rows[0].model_copy(update={"slr": "sta001.slr"}), sta.rows[1])
    fixed_sta = sta.model_copy(update={"rows": rows})
    fixed_codes = clean_setup_project.codes_bsn.model_copy(update={"pet": 1})
    project = clean_setup_project.model_copy(
        update={"codes_bsn": fixed_codes, "weather_sta": fixed_sta}
    )
    findings = _findings(project)
    assert sorted(f.evidence["variable"] for f in findings) == ["hmd", "wnd"]


def test_pet_read_from_file_flags_stations_missing_pet_file(
    clean_setup_project: TxtInOutProject,
) -> None:
    # Fixture has pet=null on every row; switching codes.bsn.pet to 4
    # requires every station to name a pet file.
    fixed = clean_setup_project.codes_bsn.model_copy(update={"pet": 4})
    project = clean_setup_project.model_copy(update={"codes_bsn": fixed})
    findings = _findings(project)
    assert len(findings) == 1
    assert findings[0].evidence["pet"] == 4
    assert set(findings[0].evidence["stations"]) == {"sta001", "sta002"}
