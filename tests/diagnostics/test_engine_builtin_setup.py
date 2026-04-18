"""End-to-end tests for ``DiagnosticEngine.from_builtin_rules()`` on the
slice-4.2 ``setup.*`` rule set.

Covers what the per-rule files cannot: that no two rules collide, that a
clean project produces zero findings, that a deliberately-broken project
fires exactly the five expected ids, and that rules tagged ``setup`` are
correctly excluded from ``evaluation`` runs.
"""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine
from swatplus_ai.parser.inputs.management_sch import (
    ManagementSchedule,
    ScheduledOp,
)
from swatplus_ai.parser.txtinout import TxtInOutProject

_EXPECTED_IDS = {
    "setup.files_present",
    "setup.mgt_date_order",
    "setup.object_count_consistency",
    "setup.sim_period_sanity",
    "setup.warmup_ratio",
}


def test_clean_project_produces_no_findings(
    clean_setup_project: TxtInOutProject,
) -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    findings = engine.run(clean_setup_project, stage="setup")
    assert findings == []


def test_broken_project_fires_all_five_rules(
    clean_setup_project: TxtInOutProject,
) -> None:
    # 1. files_present — drop object_cnt.
    # 2. sim_period_sanity — invert the year range.
    # 3. warmup_ratio — non-zero nyskip is irrelevant; inversion takes
    #    precedence. Use a cleanly-long span with bad nyskip so warm-up
    #    fires independently.
    # A single project with all five mismatches can't also invert the
    # years (that would disable warmup_ratio). Instead, use a very long
    # span with a wasteful nyskip so warm-up fires, zero-length single
    # year for sim-period, mismatched object counts, and an out-of-order
    # schedule — plus delete object_cnt AFTER reading it to trigger the
    # files-present rule while still keeping counts on the cloned one.
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
    # Drop file_cio via reference to still have object_cnt-driven rules
    # fire (we deliberately keep object_cnt present so the ``requires``
    # gate lets setup.object_count_consistency run). files_present is
    # instead fired by driving nyskip high enough to also fire warm-up,
    # and by blanking ``codes_bsn`` which is required on the parser side
    # but tolerated as ``None`` on the pydantic model — exactly the
    # "file present but unparseable" scenario the rule targets.
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
    assert ids == _EXPECTED_IDS


def test_evaluation_stage_emits_nothing(
    clean_setup_project: TxtInOutProject,
) -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    assert engine.run(clean_setup_project, stage="evaluation") == []


def test_calibration_stage_emits_nothing(
    clean_setup_project: TxtInOutProject,
) -> None:
    engine = DiagnosticEngine.from_builtin_rules()
    assert engine.run(clean_setup_project, stage="calibration") == []
