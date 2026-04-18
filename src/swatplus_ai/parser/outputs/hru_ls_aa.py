"""Parser for ``hru_ls_aa.txt`` — per-HRU annual-average land-surface.

Per-HRU version of :mod:`basin_ls_aa`: sediment yield, sediment-associated
N / P, surface-runoff nitrate / labile-P, USLE soil-loss summary,
lateral / tile nitrate, leached and tile labile-P, saturated-excess N,
and the HRU plant-cover / management / percolating-nitrate labels.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "sedyld", "sedorgn", "sedorgp", "surqno3", "lat3no3", "surqsolp",
    "usle", "sedminp", "tileno3", "lchlabp", "tilelabp", "satexn",
    "plant_cov", "mgt_ops", "percn",
)  # fmt: skip


def parse_hru_ls_aa(path: Path) -> pd.DataFrame:
    """Parse ``hru_ls_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS, text_merge_col="plant_cov")
