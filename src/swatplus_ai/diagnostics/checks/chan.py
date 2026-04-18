"""Pre-run ``chan.*`` diagnostic checks.

Channels are SWAT+'s primary routing objects: every HRU drains into a
routing unit, every routing unit into a channel, and channels carry
water (and sediment / nutrients) downstream through a DAG of ``sdc``
edges declared in ``chandeg.con``'s trailing connection 4-tuples. A
malformed topology — a cycle, a dangling ``obj_id``, no outfall, a
``frac`` block that doesn't sum to 1 — doesn't stop SWAT+ from
starting; it silently produces routed fluxes that are arithmetically
consistent but hydrologically wrong. This module front-loads those
structural checks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from swatplus_ai.diagnostics.registry import CheckResult, register_check

if TYPE_CHECKING:
    from swatplus_ai.parser.inputs.chandeg_con import ChandegCon, ChandegConRow
    from swatplus_ai.parser.txtinout import TxtInOutProject


_FRAC_TOL = 1e-3
# SWAT+ treats any ``obj_typ`` starting with "sdc" (plus a handful of
# historic aliases) as a degrading-channel edge. We only follow those
# when walking the topology — edges pointing to aquifers / reservoirs /
# other non-channel objects leave the channel subgraph and are out of
# scope for cycle detection inside ``chandeg.con``.
_CHANNEL_OBJ_TYPES: frozenset[str] = frozenset({"sdc"})


def _row_total_channel_edges(row: ChandegConRow) -> int:
    return sum(1 for c in row.connections if c.obj_typ in _CHANNEL_OBJ_TYPES)


def _check_outfall_exists(chandeg: ChandegCon) -> CheckResult | None:
    """Emit a finding when no row qualifies as an outfall.

    A row is an outfall if it has ``out_tot == 0`` or lists zero channel
    edges. Without one, SWAT+ has no sink for accumulated flow and the
    routing DAG is guaranteed to contain a cycle (pigeonhole: finite
    nodes, every node has an out-edge, so following edges must revisit).
    """
    for row in chandeg.rows:
        if row.out_tot == 0 or _row_total_channel_edges(row) == 0:
            return None
    reason = "chandeg.con has no outfall: every channel routes to another channel"
    return CheckResult(
        location="chandeg.con",
        evidence={"reason": reason, "row_count": len(chandeg.rows)},
    )


def _check_row_counts_and_fracs(row: ChandegConRow) -> list[CheckResult]:
    """Emit per-row findings for out_tot mismatch and frac-sum drift.

    ``out_tot`` is the Fortran array length the simulator allocates, so
    a mismatch with ``len(connections)`` is a hard error. The frac-sum
    check is downgraded to warning because SWAT+ itself tolerates minor
    floating-point drift in editor-exported files.
    """
    results: list[CheckResult] = []
    actual = len(row.connections)
    location = f"chandeg.con:{row.name}"
    if actual != row.out_tot:
        reason = (
            f"chandeg.con row {row.name!r}: declared out_tot={row.out_tot} "
            f"but has {actual} connection block(s)"
        )
        results.append(
            CheckResult(
                location=location,
                evidence={
                    "reason": reason,
                    "row": row.name,
                    "declared": row.out_tot,
                    "actual": actual,
                },
            ),
        )
    if row.connections:
        frac_sum = sum(c.frac for c in row.connections)
        if abs(frac_sum - 1.0) > _FRAC_TOL:
            reason = (
                f"chandeg.con row {row.name!r}: connection fractions sum to {frac_sum:.4f}, "
                f"expected 1.0 (±{_FRAC_TOL})"
            )
            results.append(
                CheckResult(
                    location=location,
                    evidence={
                        "reason": reason,
                        "row": row.name,
                        "frac_sum": round(frac_sum, 6),
                    },
                    severity="warning",
                ),
            )
    return results


def _check_downstream_in_range(row: ChandegConRow, n_rows: int) -> list[CheckResult]:
    """Flag any channel edge whose ``obj_id`` falls outside ``[1, n_rows]``."""
    results: list[CheckResult] = []
    location = f"chandeg.con:{row.name}"
    for idx, conn in enumerate(row.connections):
        if conn.obj_typ not in _CHANNEL_OBJ_TYPES:
            continue
        if conn.obj_id < 1 or conn.obj_id > n_rows:
            reason = (
                f"chandeg.con row {row.name!r}: connection #{idx + 1} points to "
                f"{conn.obj_typ} id={conn.obj_id}, out of range 1..{n_rows}"
            )
            results.append(
                CheckResult(
                    location=location,
                    evidence={
                        "reason": reason,
                        "row": row.name,
                        "conn_index": idx + 1,
                        "obj_typ": conn.obj_typ,
                        "obj_id": conn.obj_id,
                    },
                ),
            )
    return results


def _detect_cycles(chandeg: ChandegCon) -> list[CheckResult]:
    """DFS over sdc→sdc edges. Emit one finding per distinct cycle.

    Uses a three-colour scheme (WHITE/GREY/BLACK): an edge that lands on
    a GREY node closes a back-edge and reconstructs the cycle from the
    current DFS stack. Nodes are identified by 1-based ``id``; recursion
    is fine at watershed scale (hundreds to low-thousands of channels).
    Out-of-range or non-sdc edges are skipped here — they're reported by
    :func:`_check_downstream_in_range` and don't need to poison cycle
    detection. Cycles are keyed by their sorted node-id tuple so the
    same loop discovered from two entry points isn't reported twice.
    """
    rows_by_id = {row.id: row for row in chandeg.rows}
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[int, int] = {rid: WHITE for rid in rows_by_id}
    stack: list[int] = []
    seen_cycles: set[tuple[int, ...]] = set()
    results: list[CheckResult] = []

    def visit(node_id: int) -> None:
        color[node_id] = GREY
        stack.append(node_id)
        row = rows_by_id[node_id]
        for conn in row.connections:
            if conn.obj_typ not in _CHANNEL_OBJ_TYPES:
                continue
            target = conn.obj_id
            if target not in rows_by_id:
                continue
            if color[target] == GREY:
                start = stack.index(target)
                cycle_ids = (*stack[start:], target)
                key = tuple(sorted(set(cycle_ids[:-1])))
                if key in seen_cycles:
                    continue
                seen_cycles.add(key)
                names = [rows_by_id[i].name for i in cycle_ids]
                cycle_repr = " -> ".join(names)
                reason = f"chandeg.con routing cycle detected: {cycle_repr}"
                results.append(
                    CheckResult(
                        location="chandeg.con",
                        evidence={
                            "reason": reason,
                            "cycle": cycle_repr,
                            "row_ids": list(cycle_ids),
                        },
                    ),
                )
            elif color[target] == WHITE:
                visit(target)
        stack.pop()
        color[node_id] = BLACK

    for rid in rows_by_id:
        if color[rid] == WHITE:
            visit(rid)
    return results


@register_check("chan_routing_topology")
def chan_routing_topology(project: TxtInOutProject) -> list[CheckResult]:
    """Flag every structural problem in ``chandeg.con`` routing topology."""
    chandeg = project.chandeg_con
    assert chandeg is not None  # guaranteed by rule.requires gate
    results: list[CheckResult] = []
    outfall = _check_outfall_exists(chandeg)
    if outfall is not None:
        results.append(outfall)
    n_rows = len(chandeg.rows)
    for row in chandeg.rows:
        results.extend(_check_row_counts_and_fracs(row))
        results.extend(_check_downstream_in_range(row, n_rows))
    results.extend(_detect_cycles(chandeg))
    return results


__all__ = ["chan_routing_topology"]
