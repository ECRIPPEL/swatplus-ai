"""Parser for ``channel_sdmorph_aa.txt`` — per-channel annual-average morphology.

One row per degrading channel: inflow / outflow, peak rate, sediment in
and out, washload / bedload fractions, deposition, degradation at both
the channel bottom and bank, habitat / complexity metrics, width /
depth / slope, hydraulic conductivity reach length, equivalent-depth
fluxes, nutrient totals, and bankfull-depth / velocity summaries.

``deg_btm`` and ``deg_bank`` appear twice in the SWAT+ header (once
as the bedload / bank-degradation sediment contribution, once as a
depth-of-degradation morphological state). The shared reader
disambiguates the second occurrence with a ``_2`` suffix.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "flo_in", "geo_bf", "flo_out", "peakr",
    "sed_in", "sed_out", "washld", "bedld",
    "dep", "deg_btm", "deg_bank", "hc_sed",
    "width", "depth", "slope", "deg_btm", "deg_bank", "hc_len",
    "flo_in_mm", "aqu_in_mm", "flo_out_mm",
    "sed_stor", "n_tot", "p_tot",
    "dep_bf", "velav_bf",
)  # fmt: skip


def parse_channel_sdmorph_aa(path: Path) -> pd.DataFrame:
    """Parse ``channel_sdmorph_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS)
