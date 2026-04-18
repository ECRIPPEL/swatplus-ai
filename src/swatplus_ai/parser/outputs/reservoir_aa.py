"""Parser for ``reservoir_aa.txt`` — per-reservoir annual-average state / fluxes.

One row per reservoir. Shares the three-block storage / inflow / outflow
schema used by :mod:`channel_sd_aa` and :mod:`wetland_aa`, with three
``null`` separator columns between the blocks. The shared reader renames
the repeats to ``null``, ``null_2``, ``null_3`` so the DataFrame has
unique column labels.
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
)  # fmt: skip


def parse_reservoir_aa(path: Path) -> pd.DataFrame:
    """Parse ``reservoir_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS)
