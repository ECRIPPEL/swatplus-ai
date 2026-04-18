"""Parser for ``basin_ls_aa.txt`` — basin-scale annual-average land-surface.

Covers sediment yield, sediment-associated N / P, surface-runoff nitrate
and labile-P, USLE soil-loss summary, lateral / tile-drain nitrate loads,
leached labile-P, saturated-excess nitrogen, and the terminal per-HRU
labels (``plant_cov`` / ``mgt_ops`` / ``percn``) which basin-level rows
routinely omit.
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


def parse_basin_ls_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_ls_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS, text_merge_col="plant_cov")
