"""Pre-run ``hru.*`` diagnostic checks.

HRUs are the join table at the centre of a SWAT+ project — every row in
``hru-data.hru`` names four other files (``topography.hyd``,
``hydrology.hyd``, ``soils.sol``, ``landuse.lum``) by string key. A
typo or a hand-edit that deletes a referenced row leaves a dangling
foreign key that SWAT+ itself catches only at run time, after it has
allocated arrays and started consuming wall clock. This module
front-loads those FK checks into the pre-run stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from swatplus_ai.diagnostics.registry import CheckResult, register_check

if TYPE_CHECKING:
    from swatplus_ai.parser.inputs.hru_data import HruDataRow
    from swatplus_ai.parser.txtinout import TxtInOutProject


def _collect_broken_fks(
    row: HruDataRow,
    project: TxtInOutProject,
) -> list[CheckResult]:
    """Emit one :class:`CheckResult` per unresolved FK on a single HRU row.

    Columns checked: ``lu_mgt`` → ``landuse.lum``, ``soil`` → ``soils.sol``,
    ``topo`` → ``topography.hyd``, ``hydro`` → ``hydrology.hyd``. A
    ``None`` on the row is a legal "unused slot" and is skipped.
    The weather-station FK referenced in an earlier spec draft lives on
    ``hru.con`` rather than ``hru-data.hru`` (the parser's
    :class:`HruDataRow` has no ``wst`` field), so it belongs to a
    different rule in a later slice.
    """
    location = f"hru-data.hru:row={row.id}"
    checks: tuple[tuple[str | None, str, str, object], ...] = (
        (row.lu_mgt, "lu_mgt", "landuse.lum", project.landuse_lum.by_name),
        (row.soil, "soil", "soils.sol", project.soils_sol.by_name),
        (row.topo, "topo", "topography.hyd", project.topography_hyd.by_name),
        (row.hydro, "hydro", "hydrology.hyd", project.hydrology_hyd.by_name),
    )
    results: list[CheckResult] = []
    for value, field, target, lookup in checks:
        if value is None:
            continue
        # ``lookup`` is always a bound ``by_name`` method returning a row or None.
        if lookup(value) is None:  # type: ignore[operator]
            results.append(
                CheckResult(
                    location=location,
                    evidence={
                        "row_id": row.id,
                        "field": field,
                        "value": value,
                        "target": target,
                    },
                ),
            )
    return results


@register_check("hru_fk_consistency")
def hru_fk_consistency(project: TxtInOutProject) -> list[CheckResult]:
    """Flag every ``hru-data.hru`` cell whose FK does not resolve."""
    results: list[CheckResult] = []
    for row in project.hru_data.rows:
        results.extend(_collect_broken_fks(row, project))
    return results


__all__ = ["hru_fk_consistency"]
