"""Parser for ``hru_ls_aa.txt`` — per-HRU annual-average land-surface.

Per-HRU version of :mod:`basin_ls_aa`: sediment yield, sediment-associated
N / P, surface-runoff nitrate / labile-P, USLE soil-loss summary,
lateral / tile nitrate, leached and tile labile-P, saturated-excess N.
The trailing ``plant_cov`` / ``mgt_ops`` / ``percn`` labels are the HRU
plant-cover / management / percolating-nitrate markers — usually present
at HRU scope but absent when the companion modules are off. The
variable-suffix reader accepts either shape.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output_variable

_CORE_HEADER: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "sedyld", "sedorgn", "sedorgp", "surqno3", "lat3no3", "surqsolp",
    "usle", "sedminp", "tileno3", "lchlabp", "tilelabp", "satexn",
)  # fmt: skip


def parse_hru_ls_aa(path: Path) -> pd.DataFrame:
    """Parse ``hru_ls_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(
        path,
        core_columns=_CORE_HEADER,
        optional_columns=("plant_cov", "mgt_ops", "percn"),
        text_merge_col="plant_cov",
    )
