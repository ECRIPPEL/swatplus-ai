"""Tests for ``swatplus_ai.diagnostics.engine.DiagnosticEngine``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics import CheckResult, DiagnosticEngine, register_check
from swatplus_ai.parser.txtinout import TxtInOutProject


def _register_synthetic_checks() -> None:
    @register_check("_test_always_flag")
    def _flag(project: TxtInOutProject) -> CheckResult:
        return CheckResult(location="test.location", evidence={"value": 42})

    @register_check("_test_never_runs")
    def _never(project: TxtInOutProject) -> CheckResult:
        raise AssertionError("_test_never_runs should have been skipped by requires")

    @register_check("_test_multi_result")
    def _multi(project: TxtInOutProject) -> list[CheckResult]:
        return [
            CheckResult(location="item-a", evidence={"name": "alpha"}),
            CheckResult(location="item-b", evidence={"name": "beta"}),
        ]


@pytest.fixture
def engine(
    clean_registry: None,
    rule_fixtures_dir: Path,
) -> DiagnosticEngine:
    _register_synthetic_checks()
    return DiagnosticEngine.from_directory(rule_fixtures_dir)


def test_engine_loads_rules_sorted(engine: DiagnosticEngine) -> None:
    ids = [r.id for r in engine.rules]
    assert ids == [
        "test.always_flag",
        "test.multi_result",
        "test.requires_missing",
        "test.wrong_stage",
    ]


def test_engine_runs_flag_and_multi_skip_others(
    engine: DiagnosticEngine, minimal_project: Path
) -> None:
    project = TxtInOutProject.read(minimal_project)
    findings = engine.run(project, stage="setup")

    ids = sorted(f.id for f in findings)
    # always_flag + two multi_result findings; wrong_stage and requires_missing skipped.
    assert ids == ["test.always_flag", "test.multi_result", "test.multi_result"]

    always = next(f for f in findings if f.id == "test.always_flag")
    assert always.severity == "warning"
    assert always.location == "test.location"
    assert "42" in always.message
    assert always.references == ("synthetic_ref",)
    assert always.rule_ref == "test.always_flag"

    multi = [f for f in findings if f.id == "test.multi_result"]
    names = sorted(f.evidence["name"] for f in multi)
    assert names == ["alpha", "beta"]


def test_engine_stage_filter(engine: DiagnosticEngine, minimal_project: Path) -> None:
    project = TxtInOutProject.read(minimal_project)
    findings = engine.run(project, stage="calibration")
    # Only wrong_stage is tagged calibration, and its check is _test_always_flag
    # which is registered — so it fires exactly once.
    ids = [f.id for f in findings]
    assert ids == ["test.wrong_stage"]


def test_engine_unknown_check_raises_at_construction(clean_registry: None, tmp_path: Path) -> None:
    (tmp_path / "orphan.yaml").write_text(
        "\n".join(
            [
                "id: test.orphan",
                "severity: error",
                "stage: [setup]",
                "check: _test_not_registered",
                "message: orphan rule",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(KeyError, match="No check registered"):
        DiagnosticEngine.from_directory(tmp_path)


def test_engine_duplicate_rule_id_raises(clean_registry: None, tmp_path: Path) -> None:
    @register_check("_dup_check")
    def _fn(project: TxtInOutProject) -> None:
        return None

    body = "\n".join(
        [
            "id: test.dup",
            "severity: warning",
            "stage: [setup]",
            "check: _dup_check",
            "message: hi",
        ]
    )
    (tmp_path / "a.yaml").write_text(body, encoding="utf-8")
    (tmp_path / "b.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate rule id"):
        DiagnosticEngine.from_directory(tmp_path)


def test_from_directory_missing_dir_raises(clean_registry: None, tmp_path: Path) -> None:
    with pytest.raises(NotADirectoryError):
        DiagnosticEngine.from_directory(tmp_path / "nope")


def test_from_builtin_rules_loads_setup_slice(clean_registry: None) -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    # Slice 4.2 ships five pre-run ``setup.*`` rules. Assert the exact
    # set so accidental additions or deletions fail this test loudly.
    ids = {rule.id for rule in engine.rules}
    assert ids == {
        "setup.files_present",
        "setup.mgt_date_order",
        "setup.object_count_consistency",
        "setup.sim_period_sanity",
        "setup.warmup_ratio",
    }


def test_engine_skips_rule_whose_requires_is_unresolved(
    engine: DiagnosticEngine, minimal_project: Path
) -> None:
    project = TxtInOutProject.read(minimal_project)
    findings = engine.run(project, stage="setup")
    # test.requires_missing references a nonexistent attribute — skipped.
    assert not any(f.id == "test.requires_missing" for f in findings)


def test_engine_check_errors_propagate(
    clean_registry: None, tmp_path: Path, minimal_project: Path
) -> None:
    @register_check("_test_boom")
    def _boom(project: TxtInOutProject) -> None:
        raise RuntimeError("boom")

    (tmp_path / "boom.yaml").write_text(
        "\n".join(
            [
                "id: test.boom",
                "severity: error",
                "stage: [setup]",
                "check: _test_boom",
                "message: should not be seen",
            ]
        ),
        encoding="utf-8",
    )
    engine = DiagnosticEngine.from_directory(tmp_path)
    project = TxtInOutProject.read(minimal_project)
    with pytest.raises(RuntimeError, match="boom"):
        engine.run(project, stage="setup")


def test_engine_check_requires_resolves_outputs_namespace(
    clean_registry: None, tmp_path: Path, minimal_project: Path
) -> None:
    fired: list[str] = []

    @register_check("_test_needs_basin_wb_aa")
    def _needs(project: TxtInOutProject) -> CheckResult:
        fired.append(project.folder.name)
        return CheckResult(evidence={})

    (tmp_path / "needs.yaml").write_text(
        "\n".join(
            [
                "id: test.needs_basin_wb_aa",
                "severity: info",
                "stage: [setup]",
                "requires: [basin_wb_aa]",
                "check: _test_needs_basin_wb_aa",
                "message: basin_wb_aa resolved",
            ]
        ),
        encoding="utf-8",
    )
    engine = DiagnosticEngine.from_directory(tmp_path)
    project = TxtInOutProject.read(minimal_project)
    findings = engine.run(project)
    # The minimal fixture ships basin_wb_aa.txt, so the requires resolves and
    # the check fires exactly once.
    assert len(findings) == 1
    assert fired == [minimal_project.name]
