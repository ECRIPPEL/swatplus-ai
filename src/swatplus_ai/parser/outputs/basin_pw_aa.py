"""Parser for ``basin_pw_aa.txt`` — basin-scale annual-average plant / weather.

One data row per basin. ``_CORE_HEADER`` covers LAI, biomass, yield,
residue, soil temperature, plant stress factors (water / aeration /
temperature / nitrogen / phosphorus / salinity), nplt, percn, pplnt,
weather averages (tmx / tmn / tmpav / solarad / wndspd / rhum), PHU, and
plant-growth summary. The trailing ``plant_cov`` / ``mgt_ops`` labels
live on the Fortran ``output_plantweather_header`` struct and are only
written when the run has HRU-scope context — basin-scope outputs omit
them legitimately.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output_variable

_CORE_HEADER: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "lai", "bioms", "yield", "residue", "sol_tmp",
    "strsw", "strsa", "strstmp", "strsn", "strsp", "strss",
    "nplt", "percn", "pplnt",
    "tmx", "tmn", "tmpav", "solarad", "wndspd", "rhum",
    "phubas0", "lai_max", "bm_max", "bm_grow", "c_gro",
)  # fmt: skip


def parse_basin_pw_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_pw_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(path, core_columns=_CORE_HEADER, text_merge_col="plant_cov")
