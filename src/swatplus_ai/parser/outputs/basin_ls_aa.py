"""Parser for ``basin_ls_aa.txt`` — basin-scale annual-average land-surface.

Covers sediment yield, sediment-associated N / P, surface-runoff nitrate
and labile-P, USLE soil-loss summary, lateral / tile-drain nitrate loads,
leached labile-P, saturated-excess nitrogen. ``_CORE_HEADER`` mirrors
the Fortran ``output_nutcarb_ls`` physical fields (see
https://github.com/swat-model/swatplus/blob/main/src/output_landscape_module.f90).
The trailing ``plant_cov`` / ``mgt_ops`` / ``percn`` labels live on the
separate header struct and are appended only when the writer has HRU-
scope context; basin-level outputs legitimately omit them. Absence is
not drift — the variable-suffix reader silently accepts either shape.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output_variable

_CORE_HEADER: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "sedyld", "sedorgn", "sedorgp", "surqno3", "lat3no3", "surqsolp",
    "usle", "sedminp", "tileno3", "lchlabp", "tilelabp", "satexn",
)  # fmt: skip


def parse_basin_ls_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_ls_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(
        path,
        core_columns=_CORE_HEADER,
        optional_columns=("plant_cov", "mgt_ops", "percn"),
        text_merge_col="plant_cov",
    )
