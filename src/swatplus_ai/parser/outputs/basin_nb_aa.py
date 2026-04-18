"""Parser for ``basin_nb_aa.txt`` — basin-scale annual-average nutrient balance.

Grazing / fertilizer / fixation / denitrification / mineralization fluxes
across the nitrogen and phosphorus cycles, atmospheric deposition,
plant uptake, and groundwater-to-soil contributions. Basin-level rows
often omit the trailing ``plant_cov`` / ``mgt_ops`` labels; short rows
are padded with NaN.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "grzn", "grzp", "lab_min_p", "act_sta_p",
    "fertn", "fertp", "fixn", "denit",
    "act_nit_n", "act_sta_n", "org_lab_p",
    "rsd_nitorg_n", "rsd_laborg_p",
    "no3atmo", "nh4atmo", "nuptake", "puptake",
    "gwsoiln", "gwsoilp",
    "plant_cov", "mgt_ops",
)  # fmt: skip


def parse_basin_nb_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_nb_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS, text_merge_col="plant_cov")
