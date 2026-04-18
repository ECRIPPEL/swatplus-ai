"""End-to-end tests for ``DiagnosticEngine.from_builtin_rules()`` on the
Module-1 rule set closed out in slice 4.3.

Covers what the per-rule files cannot: that no two rules collide, that a
clean project produces zero findings, that a deliberately-broken project
fires exactly the five expected ``setup.*`` ids, and that stage
filtering correctly separates pre-run (``setup``) from post-run
(``evaluation``) rules.
"""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine
from swatplus_ai.parser.inputs.management_sch import (
    ManagementSchedule,
    ScheduledOp,
)
from swatplus_ai.parser.txtinout import TxtInOutProject

_EXPECTED_RULE_IDS = {
    "chan.routing_topology",
    "hru.fk_consistency",
    "setup.files_present",
    "setup.mgt_date_order",
    "setup.object_count_consistency",
    "setup.pet_method_vs_climate",
    "setup.sim_period_sanity",
    "setup.warmup_ratio",
    "wb.et_precip_ratio",
    "wx.source_consistency",
}


def test_from_builtin_rules_loads_all_ten() -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    ids = {rule.id for rule in engine.rules}
    assert ids == _EXPECTED_RULE_IDS


def test_clean_project_produces_no_findings(
    clean_setup_project: TxtInOutProject,
) -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    findings = engine.run(clean_setup_project, stage="setup")
    assert findings == []


def test_broken_project_fires_all_five_setup_rules(
    clean_setup_project: TxtInOutProject,
) -> None:
    # A single project with all five setup.* mismatches can't also invert
    # the years (that would disable warmup_ratio). Instead, use a very
    # long span with a wasteful nyskip so warm-up fires, zero-length
    # single year for sim-period, mismatched object counts, and an
    # out-of-order schedule — plus drop codes_bsn so files-present fires
    # the "file present but unparseable" scenario it targets.
    bad_time = clean_setup_project.time_sim.model_copy(
        update={"yrc_start": 2005, "yrc_end": 2005, "day_start": 200, "day_end": 100}
    )
    assert clean_setup_project.object_cnt is not None
    bad_cnt = clean_setup_project.object_cnt.model_copy(update={"hru": 99})
    bad_schedule = ManagementSchedule(
        name="bad_sched",
        numb_ops=2,
        numb_auto=0,
        ops=(
            ScheduledOp(
                op_typ="plnt",
                mon=9,
                day=1,
                hu_sch=0.0,
                op_data1=None,
                op_data2=None,
                op_data3=0.0,
            ),
            ScheduledOp(
                op_typ="hvkl",
                mon=4,
                day=1,
                hu_sch=0.0,
                op_data1=None,
                op_data2=None,
                op_data3=0.0,
            ),
        ),
        autos=(),
    )
    bad_mgt = clean_setup_project.management_sch.model_copy(update={"schedules": (bad_schedule,)})
    broken = clean_setup_project.model_copy(
        update={
            "time_sim": bad_time,
            "print_prt": clean_setup_project.print_prt.model_copy(update={"nyskip": 20}),
            "object_cnt": bad_cnt,
            "management_sch": bad_mgt,
            "codes_bsn": None,
        }
    )
    engine = DiagnosticEngine.from_builtin_rules()
    findings = engine.run(broken, stage="setup")
    ids = {f.id for f in findings}
    assert ids == {
        "setup.files_present",
        "setup.mgt_date_order",
        "setup.object_count_consistency",
        "setup.sim_period_sanity",
        "setup.warmup_ratio",
    }


def test_evaluation_stage_only_runs_evaluation_rules(
    clean_setup_project: TxtInOutProject,
) -> None:
    # On a project with no outputs loaded, the evaluation-stage rule's
    # `requires` gate skips it — so the stage filter produces an empty
    # list exactly like setup did on a clean project.
    engine = DiagnosticEngine.from_builtin_rules()
    assert engine.run(clean_setup_project, stage="evaluation") == []


def test_calibration_stage_emits_nothing(
    clean_setup_project: TxtInOutProject,
) -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    assert engine.run(clean_setup_project, stage="calibration") == []
