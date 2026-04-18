"""Pre-run ``wx.*`` diagnostic checks for weather-input consistency.

The SWAT+ climate wiring is spread across two layers: the per-station
table ``weather-sta.cli`` names a filename for each of five observed
variables (``pcp``, ``tmp``, ``slr``, ``hmd``, ``wnd``), and the
per-variable index files (``pcp.cli`` ...) list every filename the
simulator should open. Both must agree — a filename present on a
station row but absent from the matching index is silently ignored by
SWAT+ (the variable falls through to WGN), and a filename present in
the index but missing from disk aborts the run partway.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from swatplus_ai.diagnostics.registry import CheckResult, register_check

if TYPE_CHECKING:
    from swatplus_ai.parser.txtinout import TxtInOutProject


_WX_VAR_FILES: tuple[tuple[str, str, str], ...] = (
    ("pcp", "pcp_cli", "pcp.cli"),
    ("tmp", "tmp_cli", "tmp.cli"),
    ("slr", "slr_cli", "slr.cli"),
    ("hmd", "hmd_cli", "hmd.cli"),
    ("wnd", "wnd_cli", "wnd.cli"),
)


@register_check("wx_source_consistency")
def wx_source_consistency(project: TxtInOutProject) -> list[CheckResult]:
    """Cross-check ``weather-sta.cli`` against each per-variable index.

    Two failure modes, both reported as distinct findings:

    * **Forward gap** — station row names an observed filename for a
      variable, but that filename is absent from the per-variable index.
      SWAT+ silently treats the station as WGN-simulated for that
      variable, making runs look healthy while the observed record
      never reaches the simulator.
    * **Reverse gap** — a filename listed in a ``*.cli`` index file is
      not on disk. SWAT+ aborts partway through the run after having
      already consumed wall time.

    Variables whose index file is ``None`` are skipped entirely — that
    ``.cli`` file is optional at the project level.
    """
    results: list[CheckResult] = []
    for var, cli_attr, cli_name in _WX_VAR_FILES:
        cli = getattr(project, cli_attr)
        if cli is None:
            continue
        index = set(cli.filenames)
        for row in project.weather_sta.rows:
            value = getattr(row, var)
            if value is None or value == "sim":
                continue
            if value not in index:
                reason = (
                    f"weather-sta.cli row {row.name!r}: {var}={value!r} is not listed in {cli_name}"
                )
                results.append(
                    CheckResult(
                        location=f"weather-sta.cli:{row.name}:{var}",
                        evidence={
                            "reason": reason,
                            "station": row.name,
                            "variable": var,
                            "filename": value,
                            "index": cli_name,
                        },
                    ),
                )
        for fname in cli.filenames:
            if not (project.folder / fname).is_file():
                reason = (
                    f"{cli_name} references {fname!r}, but the file is not present in the "
                    f"project folder"
                )
                results.append(
                    CheckResult(
                        location=f"{cli_name}:{fname}",
                        evidence={
                            "reason": reason,
                            "index": cli_name,
                            "filename": fname,
                        },
                    ),
                )
    return results


__all__ = ["wx_source_consistency"]
