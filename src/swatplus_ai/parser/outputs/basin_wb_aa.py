"""Parser for ``basin_wb_aa.txt`` — basin-scale annual-average water balance.

One data row per basin (usually one). Columns cover precipitation, snow,
surface / lateral / return flow, ET components, CN, soil-water, PET,
irrigation, wetland fluxes, and the terminal plant-cover / management-
operation labels. Basin-level files report ``plant_cov`` as a free-text
multi-word label (e.g. ``"Original Simulation"``) which the shared reader
folds back together via ``text_merge_col``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output

_COLUMNS: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "precip", "snofall", "snomlt", "surq_gen", "latq", "wateryld", "perc",
    "et", "ecanopy", "eplant", "esoil", "surq_cont", "cn",
    "sw_init", "sw_final", "sw_ave", "sw_300", "sno_init", "sno_final", "snopack",
    "pet", "qtile", "irr", "surq_runon", "latq_runon", "overbank",
    "surq_cha", "surq_res", "surq_ls", "latq_cha", "latq_res", "latq_ls",
    "gwsoilq", "satex", "satex_chan", "sw_change",
    "lagsurf", "laglatq", "lagsatex",
    "wet_evap", "wet_oflo", "wet_stor",
    "plant_cov", "mgt_ops",
)  # fmt: skip


def parse_basin_wb_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_wb_aa.txt`` into a DataFrame."""
    return read_aa_output(path, expected_columns=_COLUMNS, text_merge_col="plant_cov")
