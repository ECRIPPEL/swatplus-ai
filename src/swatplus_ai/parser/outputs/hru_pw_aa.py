"""Parser for ``hru_pw_aa.txt`` — per-HRU annual-average plant / weather.

Per-HRU version of :mod:`basin_pw_aa`: one row per HRU with LAI, biomass,
yield, residue, soil temperature, stress factors, plant population,
percolating nitrate, weather averages and plant-growth summary. At HRU
scope the ``plant_cov`` / ``mgt_ops`` labels are almost always emitted;
the variable-suffix reader accepts their absence so runs that disable
plant-growth output still parse cleanly.
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


def parse_hru_pw_aa(path: Path) -> pd.DataFrame:
    """Parse ``hru_pw_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(path, core_columns=_CORE_HEADER, text_merge_col="plant_cov")
