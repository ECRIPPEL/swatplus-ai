"""Parser for ``basin_nb_aa.txt`` — basin-scale annual-average nutrient balance.

Grazing / fertilizer / fixation / denitrification / mineralization fluxes
across the nitrogen and phosphorus cycles, atmospheric deposition,
plant uptake, and groundwater-to-soil contributions. ``_CORE_HEADER``
mirrors the Fortran physical fields in ``output_landscape_module.f90``.
The trailing ``plant_cov`` / ``mgt_ops`` labels come from the companion
header struct and are appended only for HRU-scope outputs — basin rows
routinely stop at ``gwsoilp``. The variable-suffix reader accepts both
shapes silently; absence is module-conditional output, not drift.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output_variable

_CORE_HEADER: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "grzn", "grzp", "lab_min_p", "act_sta_p",
    "fertn", "fertp", "fixn", "denit",
    "act_nit_n", "act_sta_n", "org_lab_p",
    "rsd_nitorg_n", "rsd_laborg_p",
    "no3atmo", "nh4atmo", "nuptake", "puptake",
    "gwsoiln", "gwsoilp",
)  # fmt: skip


def parse_basin_nb_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_nb_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(path, core_columns=_CORE_HEADER, text_merge_col="plant_cov")
