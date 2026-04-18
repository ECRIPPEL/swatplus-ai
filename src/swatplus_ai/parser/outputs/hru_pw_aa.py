"""Parser for ``hru_pw_aa.txt`` — per-HRU annual-average plant / weather.

Per-HRU version of :mod:`basin_pw_aa`: one row per HRU with LAI, biomass,
yield, residue, soil temperature, stress factors, plant population,
percolating nitrate, pounds-phosphorus, weather averages and plant-growth
summary.
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


def parse_hru_pw_aa(path: Path) -> pd.DataFrame:
    """Parse ``hru_pw_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS, text_merge_col="plant_cov")
