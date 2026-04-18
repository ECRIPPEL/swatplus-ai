"""Parser for ``wetland_aa.txt`` — per-wetland annual-average state / fluxes.

Shares the three-block storage / inflow / outflow schema used by
:mod:`reservoir_aa` and :mod:`channel_sd_aa`; the repeated ``null``
separators are disambiguated by the shared reader.
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


def parse_wetland_aa(path: Path) -> pd.DataFrame:
    """Parse ``wetland_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS)
