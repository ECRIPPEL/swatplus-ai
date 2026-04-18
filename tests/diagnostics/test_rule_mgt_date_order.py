"""Tests for rule ``setup.mgt_date_order``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.inputs.management_sch import (
    ManagementSchedule,
    ScheduledOp,
)
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _mgt_findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="setup") if f.id == "setup.mgt_date_order"]


def _with_schedules(
    project: TxtInOutProject, schedules: tuple[ManagementSchedule, ...]
) -> TxtInOutProject:
    new_mgt = project.management_sch.model_copy(update={"schedules": schedules})
    return project.model_copy(update={"management_sch": new_mgt})


def _date_op(op_typ: str, mon: int, day: int) -> ScheduledOp:
    return ScheduledOp(
        op_typ=op_typ,
        mon=mon,
        day=day,
        hu_sch=0.0,
        op_data1=None,
        op_data2=None,
        op_data3=0.0,
    )


def _hu_op(op_typ: str, hu_sch: float) -> ScheduledOp:
    return ScheduledOp(
        op_typ=op_typ,
        mon=0,
        day=0,
        hu_sch=hu_sch,
        op_data1=None,
        op_data2=None,
        op_data3=0.0,
    )


def _schedule(name: str, ops: tuple[ScheduledOp, ...]) -> ManagementSchedule:
    return ManagementSchedule(name=name, numb_ops=len(ops), numb_auto=0, ops=ops, autos=())


def test_mgt_date_order_clean_project(clean_setup_project: TxtInOutProject) -> None:
    # The committed soyb_rot schedule is already monotonic (3/20, 9/30, 10/1).
    assert _mgt_findings(clean_setup_project) == []


def test_mgt_date_order_detects_date_regression(
    clean_setup_project: TxtInOutProject,
) -> None:
    bad = _schedule(
        "bad_date",
        (
            _date_op("plnt", 5, 10),
            _date_op("hvkl", 3, 1),
        ),
    )
    project = _with_schedules(
        clean_setup_project,
        (*clean_setup_project.management_sch.schedules, bad),
    )
    findings = _mgt_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == "warning"
    assert f.location == "management.sch:bad_date"
    assert f.evidence == {
        "schedule": "bad_date",
        "op_index": 1,
        "prior": "05-10 (plnt)",
        "current": "03-01 (hvkl)",
    }
    assert "out-of-order" in f.message


def test_mgt_date_order_detects_hu_regression(
    clean_setup_project: TxtInOutProject,
) -> None:
    bad = _schedule(
        "bad_hu",
        (
            _hu_op("plnt", 0.3),
            _hu_op("hvkl", 0.1),
        ),
    )
    project = _with_schedules(clean_setup_project, (bad,))
    findings = _mgt_findings(project)
    assert len(findings) == 1
    f = findings[0]
    assert f.evidence["op_index"] == 1
    assert "hu_sch=0.3000" in f.evidence["prior"]
    assert "hu_sch=0.1000" in f.evidence["current"]


def test_mgt_date_order_skips_mixed_regime(
    clean_setup_project: TxtInOutProject,
) -> None:
    mixed = _schedule(
        "mixed",
        (
            _date_op("plnt", 5, 10),
            _hu_op("hvkl", 0.2),
        ),
    )
    project = _with_schedules(clean_setup_project, (mixed,))
    assert _mgt_findings(project) == []


def test_mgt_date_order_skips_single_op_and_empty(
    clean_setup_project: TxtInOutProject,
) -> None:
    empty = _schedule("empty", ())
    one = _schedule("one", (_date_op("plnt", 4, 1),))
    project = _with_schedules(clean_setup_project, (empty, one))
    assert _mgt_findings(project) == []
