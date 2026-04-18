"""Parser for ``aquifer_aa.txt`` — per-aquifer annual-average state / fluxes.

One row per aquifer (``aqu###``). Columns include baseflow, depth to
water table, storage, recharge, seepage, revap, nitrate storage and
loads (lateral, percolated, seeped), mineral P, organic N and P, and
the split of outflow to channels / reservoirs / landscape.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "flo", "dep_wt", "stor", "rchrg", "seep", "revap",
    "no3_st", "minp", "orgn", "orgp",
    "no3_rchg", "no3_loss", "no3_lat", "no3_seep",
    "flo_cha", "flo_res", "flo_ls",
)  # fmt: skip


def parse_aquifer_aa(path: Path) -> pd.DataFrame:
    """Parse ``aquifer_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS)
