"""Pre-run ``setup.*`` diagnostic checks.

These five checks look only at parsed input files — they never require
simulation output — and together cover the structural problems that
cause SWAT+ to either refuse to start or to start and silently produce
nonsense. The SWAT+ Fortran core performs no pre-run validation (see
the 2026-04-17 prior-art audit in ``swatplus-ai_roadmap.md``), so every
finding here is a gap nothing else in the ecosystem catches before a
run wastes wall time.

Each check is bound to a YAML rule (``src/swatplus_ai/diagnostics/rules/
setup_*.yaml``) via :func:`register_check`. The rule carries severity,
stage, ``requires``, and the ``{...}``-substituted message template; the
check returns ``CheckResult`` instances whose ``evidence`` fills those
placeholders. Keeping the substitution in the rule (instead of the
check) means YAML authors can retune wording without touching Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from swatplus_ai.diagnostics.registry import CheckResult, register_check

if TYPE_CHECKING:
    from swatplus_ai.parser.inputs.management_sch import ManagementSchedule, ScheduledOp
    from swatplus_ai.parser.txtinout import TxtInOutProject


_CONTROL_FILES: tuple[tuple[str, str], ...] = (
    ("time_sim", "time.sim"),
    ("print_prt", "print.prt"),
    ("file_cio", "file.cio"),
    ("codes_bsn", "codes.bsn"),
    ("parameters_bsn", "parameters.bsn"),
    ("object_cnt", "object.cnt"),
)


@register_check("setup_files_present")
def setup_files_present(project: TxtInOutProject) -> list[CheckResult]:
    """Flag any required control file that is absent or unparseable.

    ``TxtInOutProject.read`` already raises on a missing *required* file,
    so by the time this check runs those six attributes can only be
    ``None`` for files that were declared optional at the project level
    (``object.cnt``) but are still expected for any real SWAT+ run.
    """
    results: list[CheckResult] = []
    for attr, filename in _CONTROL_FILES:
        if getattr(project, attr, None) is None:
            results.append(
                CheckResult(location=filename, evidence={"file": filename}),
            )
    return results


@register_check("setup_sim_period_sanity")
def setup_sim_period_sanity(project: TxtInOutProject) -> list[CheckResult]:
    """Catch inverted year ranges, zero-length single-year runs, and short spans.

    Three distinct branches with two severities — inversion and
    zero-length are ``error``, short span is ``warning`` — the latter
    overridden on the :class:`CheckResult` so the rule's declared
    ``error`` severity doesn't incorrectly promote it.
    """
    ts = project.time_sim
    results: list[CheckResult] = []
    location = "time.sim"

    if ts.yrc_end < ts.yrc_start:
        reason = (
            f"Simulation year range is inverted: yrc_start={ts.yrc_start}, yrc_end={ts.yrc_end}"
        )
        results.append(
            CheckResult(
                location=location,
                evidence={
                    "reason": reason,
                    "yrc_start": ts.yrc_start,
                    "yrc_end": ts.yrc_end,
                },
            ),
        )
        return results

    if ts.yrc_end == ts.yrc_start and ts.day_end <= ts.day_start:
        reason = (
            f"Single-year simulation ends at or before start: "
            f"day_start={ts.day_start}, day_end={ts.day_end}"
        )
        results.append(
            CheckResult(
                location=location,
                evidence={
                    "reason": reason,
                    "day_start": ts.day_start,
                    "day_end": ts.day_end,
                },
            ),
        )
        return results

    span = ts.yrc_end - ts.yrc_start + 1
    if span < 2:
        reason = f"Simulation span of {span} year(s) may be too short for meaningful analysis"
        results.append(
            CheckResult(
                location=location,
                evidence={"reason": reason, "span": span},
                severity="warning",
            ),
        )
    return results


@register_check("setup_bsn_day_lag_max_as_float")
def setup_bsn_day_lag_max_as_float(
    project: TxtInOutProject,
) -> CheckResult | None:
    """Warn when ``parameters.bsn`` ``day_lag_max`` was serialized as a float.

    The canonical Fortran type is integer, but SWAT+ Editor < v3.1.0 writes
    it as ``0.00000``. Fortran list-directed I/O silently tolerates this, so
    the bug is only observable at parse time on our side — surfaced here as
    an actionable upgrade hint. Observed via
    :mod:`~swatplus_ai.diagnostics.drift` during parsing.
    """
    for drift in project.drifts:
        if drift.file == "parameters.bsn" and drift.column == "day_lag_max":
            return CheckResult(
                location="parameters.bsn",
                evidence={
                    "observed": drift.observed,
                    "fixed_in_version": drift.fixed_in_version or "unknown",
                },
            )
    return None


@register_check("setup_warmup_ratio")
def setup_warmup_ratio(project: TxtInOutProject) -> CheckResult | None:
    """Warn when ``print.prt`` ``nyskip`` is implausibly low or wasteful.

    Ratio thresholds are SWAT+-community rules of thumb: the first few
    years of any simulation carry spin-up artifacts from arbitrary
    initial aquifer / soil / plant states, so below ~10 % warm-up tends
    to leave those artifacts in the analysed record; above ~33 % the
    warm-up eats a disproportionate share of an already-finite
    simulation window. Skipped when ``span <= 0`` because
    :func:`setup_sim_period_sanity` owns that failure mode.
    """
    ts = project.time_sim
    pp = project.print_prt
    span = ts.yrc_end - ts.yrc_start + 1
    if span <= 0:
        return None

    ratio = pp.nyskip / span
    if ratio < 0.10:
        reason = (
            f"Warmup ratio {ratio:.2f} is low (nyskip={pp.nyskip}, "
            f"span={span} yrs); model may carry state-initialization artifacts"
        )
    elif ratio > 0.33:
        reason = (
            f"Warmup ratio {ratio:.2f} is wastefully high (nyskip={pp.nyskip}, span={span} yrs)"
        )
    else:
        return None

    return CheckResult(
        location="print.prt",
        evidence={
            "reason": reason,
            "nyskip": pp.nyskip,
            "span": span,
            "ratio": round(ratio, 4),
        },
    )


def _op_is_hu_scheduled(op: ScheduledOp) -> bool:
    return op.hu_sch > 0.0


def _schedule_is_homogeneous(schedule: ManagementSchedule) -> bool:
    if len(schedule.ops) <= 1:
        return True
    first = _op_is_hu_scheduled(schedule.ops[0])
    return all(_op_is_hu_scheduled(op) is first for op in schedule.ops[1:])


@register_check("setup_mgt_date_order")
def setup_mgt_date_order(project: TxtInOutProject) -> list[CheckResult]:
    """Flag management schedules whose operations are not in ascending order.

    Mixed-regime schedules (some ops heat-unit-scheduled, others
    date-scheduled) are skipped: SWAT+ resolves them at runtime in a
    way that makes a purely-textual ordering check ambiguous. A one-op
    or zero-op schedule is vacuously ordered.
    """
    results: list[CheckResult] = []
    for schedule in project.management_sch.schedules:
        if len(schedule.ops) < 2 or not _schedule_is_homogeneous(schedule):
            continue
        hu_mode = _op_is_hu_scheduled(schedule.ops[0])
        prev = schedule.ops[0]
        for idx, op in enumerate(schedule.ops[1:], start=1):
            if hu_mode:
                in_order = op.hu_sch >= prev.hu_sch
                prior_repr = f"hu_sch={prev.hu_sch:.4f} ({prev.op_typ})"
                current_repr = f"hu_sch={op.hu_sch:.4f} ({op.op_typ})"
            else:
                in_order = (op.mon, op.day) >= (prev.mon, prev.day)
                prior_repr = f"{prev.mon:02d}-{prev.day:02d} ({prev.op_typ})"
                current_repr = f"{op.mon:02d}-{op.day:02d} ({op.op_typ})"
            if not in_order:
                results.append(
                    CheckResult(
                        location=f"management.sch:{schedule.name}",
                        evidence={
                            "schedule": schedule.name,
                            "op_index": idx,
                            "prior": prior_repr,
                            "current": current_repr,
                        },
                    ),
                )
            prev = op
    return results


_OBJECT_CON_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("hru", "hru_con", "hru"),
    ("cha", "chandeg_con", "cha"),
    ("aqu", "aquifer_con", "aqu"),
    ("res", "reservoir_con", "res"),
    ("rtu", "rout_unit_con", "rtu"),
)


@register_check("setup_object_count_consistency")
def setup_object_count_consistency(project: TxtInOutProject) -> list[CheckResult]:
    """Compare ``object.cnt`` declared counts against ``*.con`` actual rows.

    A mismatch means either ``object.cnt`` was hand-edited to the wrong
    number (common when users delete rows from a ``.con`` without
    regenerating the inventory) or the project is half-migrated between
    watershed delineations. Either is a hard error: SWAT+ sizes arrays
    off ``object.cnt`` and will index out-of-range on a low count or
    leak uninitialised rows on a high one.

    When the corresponding ``.con`` parser came back ``None`` (file
    absent), we skip only that pair — the ``rule.requires`` check
    already gated on ``object_cnt`` itself being present.
    """
    object_cnt = project.object_cnt
    assert object_cnt is not None  # guaranteed by rule.requires gate
    results: list[CheckResult] = []
    for obj, con_attr, obj_cnt_attr in _OBJECT_CON_PAIRS:
        con = getattr(project, con_attr)
        if con is None:
            continue
        declared = getattr(object_cnt, obj_cnt_attr)
        actual = len(con.rows)
        if declared != actual:
            results.append(
                CheckResult(
                    location="object.cnt",
                    evidence={
                        "object": obj,
                        "declared": declared,
                        "actual": actual,
                    },
                ),
            )
    return results


_PET_METHOD_NAME: dict[int, str] = {
    1: "Penman-Monteith",
    2: "Priestley-Taylor",
    3: "Hargreaves",
    4: "read-from-file",
}

_PET_REQUIRED_VARS: dict[int, tuple[str, ...]] = {
    1: ("slr", "hmd", "wnd"),
    2: ("slr", "hmd"),
    # pet=3 (Hargreaves) needs temperature only — always available — so the rule
    # is vacuously satisfied and the check emits nothing.
    3: (),
    # pet=4 handled separately: every station must point at a per-station pet file.
    4: (),
}


def _pet_var_is_simulated(value: str | None) -> bool:
    """Weather-station cell is ``sim`` (WGN-generated), not observed."""
    return value == "sim"


@register_check("setup_pet_method_vs_climate")
def setup_pet_method_vs_climate(project: TxtInOutProject) -> list[CheckResult]:
    """Warn when the chosen PET method has no observed inputs to feed it.

    PM / Priestley-Taylor need solar / humidity / wind and degrade to
    pure WGN-driven output if every station reports ``sim`` for those
    variables. Hargreaves needs only temperature (always present in
    SWAT+ projects), so it's vacuously satisfied. ``pet=4`` (read-from-
    file) needs an explicit per-station pet file on every station.
    """
    codes = project.codes_bsn
    sta = project.weather_sta
    if not sta.rows:
        return []
    pet = codes.pet
    method = _PET_METHOD_NAME.get(pet, f"code={pet}")
    location = "codes.bsn"
    results: list[CheckResult] = []

    if pet == 4:
        missing = [r.name for r in sta.rows if r.pet is None or _pet_var_is_simulated(r.pet)]
        if missing:
            reason = (
                f"codes.bsn pet={pet} ({method}) expects each station to name a pet file, "
                f"but {len(missing)} station(s) do not: {', '.join(missing)}"
            )
            results.append(
                CheckResult(
                    location=location,
                    evidence={
                        "reason": reason,
                        "pet": pet,
                        "method": method,
                        "stations": list(missing),
                    },
                ),
            )
        return results

    for var in _PET_REQUIRED_VARS.get(pet, ()):
        if all(_pet_var_is_simulated(getattr(row, var)) for row in sta.rows):
            reason = (
                f"codes.bsn pet={pet} ({method}) needs observed {var}, but every weather "
                f"station reports {var}='sim'"
            )
            results.append(
                CheckResult(
                    location=location,
                    evidence={
                        "reason": reason,
                        "pet": pet,
                        "method": method,
                        "variable": var,
                    },
                ),
            )
    return results


__all__ = [
    "setup_bsn_day_lag_max_as_float",
    "setup_files_present",
    "setup_mgt_date_order",
    "setup_object_count_consistency",
    "setup_pet_method_vs_climate",
    "setup_sim_period_sanity",
    "setup_warmup_ratio",
]
