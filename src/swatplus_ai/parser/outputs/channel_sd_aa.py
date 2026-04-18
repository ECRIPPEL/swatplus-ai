"""Parser for ``channel_sd_aa.txt`` — per-channel annual-average state / fluxes.

One row per degrading channel (``cha###``). Columns are organized in
three blocks separated by a literal ``null`` placeholder column:

* storage end-of-year (``flo_stor``, ``sed_stor``, nutrient stores,
  particle-size-class stores, gravel store);
* cumulative inflow (``flo_in``, sediment, nutrients, particle-size
  classes);
* cumulative outflow (``flo_out``, sediment, nutrients, particle-size
  classes).

The three ``null`` separator columns are disambiguated to ``null``,
``null_2``, ``null_3`` by the shared reader so the DataFrame has unique
column labels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "area", "precip", "evap", "seep",
    "flo_stor", "sed_stor", "orgn_stor", "sedp_stor", "no3_stor", "solp_stor",
    "chla_stor", "nh3_stor", "no2_stor", "cbod_stor", "dox_stor",
    "san_stor", "sil_stor", "cla_stor", "sag_stor", "lag_stor", "grv_stor",
    "null",
    "flo_in", "sed_in", "orgn_in", "sedp_in", "no3_in", "solp_in",
    "chla_in", "nh3_in", "no2_in", "cbod_in", "dox_in",
    "san_in", "sil_in", "cla_in", "sag_in", "lag_in", "grv_in",
    "null",
    "flo_out", "sed_out", "orgn_out", "sedp_out", "no3_out", "solp_out",
    "chla_out", "nh3_out", "no2_out", "cbod_out", "dox_out",
    "san_out", "sil_out", "cla_out", "sag_out", "lag_out", "grv_out",
    "null",
    "water_temp",
)  # fmt: skip


def parse_channel_sd_aa(path: Path) -> pd.DataFrame:
    """Parse ``channel_sd_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS)
