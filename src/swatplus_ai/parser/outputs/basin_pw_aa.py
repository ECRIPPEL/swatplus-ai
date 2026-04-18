"""Parser for ``basin_pw_aa.txt`` — basin-scale annual-average plant / weather.

One data row per basin. Columns cover LAI, biomass, yield, residue,
soil temperature, plant stress factors (water / aeration / temperature /
nitrogen / phosphorus / salinity), nplt, percn, pplnt, weather averages
(tmx / tmn / tmpav / solarad / wndspd / rhum), PHU, plant-growth summary
and the terminal plant-cover / management-operation labels. Basin-level
rows may omit the trailing ``plant_cov`` / ``mgt_ops`` — the shared
reader pads short rows with NaN.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "lai", "bioms", "yield", "residue", "sol_tmp",
    "strsw", "strsa", "strstmp", "strsn", "strsp", "strss",
    "nplt", "percn", "pplnt",
    "tmx", "tmn", "tmpav", "solarad", "wndspd", "rhum",
    "phubas0", "lai_max", "bm_max", "bm_grow", "c_gro",
    "plant_cov", "mgt_ops",
)  # fmt: skip


def parse_basin_pw_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_pw_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS, text_merge_col="plant_cov")
