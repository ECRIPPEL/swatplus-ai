"""Post-run ``wb.*`` water-balance diagnostic checks.

Evaluation-stage rules: they read the annual-average output files a
SWAT+ run produces, so they are only useful once a simulation has
completed. The engine's ``requires`` gate skips them automatically on
projects that haven't been run yet.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from swatplus_ai.diagnostics.registry import CheckResult, register_check

if TYPE_CHECKING:
    from swatplus_ai.parser.txtinout import TxtInOutProject


_ET_PRECIP_LOW = 0.35
_ET_PRECIP_HIGH = 0.95


@register_check("wb_et_precip_ratio")
def wb_et_precip_ratio(project: TxtInOutProject) -> list[CheckResult]:
    """Warn on implausible basin-scale ET / precipitation ratios.

    The global-climate envelope for basin-scale annual-average ET/P
    typically sits between 0.35 (arid regions with significant outflow)
    and 0.95 (semi-arid to arid where ET dominates). Values below
    suggest either a broken ET routine or a climate file that over-
    reports precipitation; values above suggest double-counted ET
    (surface + canopy + plant) or a badly miscalibrated soil store.
    Either way, the number is a first-order smell test on whether the
    run is self-consistent before any calibration effort begins.
    """
    df = project.outputs.basin_wb_aa
    assert df is not None  # rule.requires gates on outputs.basin_wb_aa
    results: list[CheckResult] = []
    for _, row in df.iterrows():
        precip = float(row["precip"])
        et = float(row["et"])
        name = str(row.get("name", "basin"))
        if precip <= 0:
            continue
        ratio = et / precip
        if ratio < _ET_PRECIP_LOW:
            reason = (
                f"basin {name!r}: ET/precip ratio {ratio:.3f} is below {_ET_PRECIP_LOW:.2f} — "
                f"ET routine may be under-reporting or precip is overestimated"
            )
        elif ratio > _ET_PRECIP_HIGH:
            reason = (
                f"basin {name!r}: ET/precip ratio {ratio:.3f} is above {_ET_PRECIP_HIGH:.2f} — "
                f"possible double-counted ET components or miscalibrated soil store"
            )
        else:
            continue
        results.append(
            CheckResult(
                location=f"basin_wb_aa.txt:{name}",
                evidence={
                    "reason": reason,
                    "name": name,
                    "precip": round(precip, 4),
                    "et": round(et, 4),
                    "ratio": round(ratio, 4),
                },
            ),
        )
    return results


__all__ = ["wb_et_precip_ratio"]
