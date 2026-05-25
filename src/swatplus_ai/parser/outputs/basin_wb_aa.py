"""Parser for ``basin_wb_aa.txt`` — basin-scale annual-average water balance.

One data row per basin (usually one). ``_CORE_HEADER`` mirrors the 42
fields of the Fortran ``output_waterbal`` type (see
https://github.com/swat-model/swatplus/blob/main/src/output_landscape_module.f90)
plus the 7 metadata columns every SWAT+ output file leads with. The
trailing ``plant_cov`` / ``mgt_ops`` labels come from the separate
``output_waterbal_header`` Fortran struct and are only emitted when the
writer has HRU-scope context to populate them — basin-scope runs with
plant growth off legitimately stop the header at ``wet_stor``. Absence
is therefore not drift; it is the simulation telling us which modules
were active, and the variable-suffix reader lets us parse either shape
silently. Basin-level files report ``plant_cov`` as a free-text
multi-word label (e.g. ``"Original Simulation"``) which the shared
reader folds back together via ``text_merge_col``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from swatplus_ai.parser.outputs._base import read_aa_output_variable

_CORE_HEADER: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "precip", "snofall", "snomlt", "surq_gen", "latq", "wateryld", "perc",
    "et", "ecanopy", "eplant", "esoil", "surq_cont", "cn",
    "sw_init", "sw_final", "sw_ave", "sw_300", "sno_init", "sno_final", "snopack",
    "pet", "qtile", "irr", "surq_runon", "latq_runon", "overbank",
    "surq_cha", "surq_res", "surq_ls", "latq_cha", "latq_res", "latq_ls",
    "gwsoilq", "satex", "satex_chan", "sw_change",
    "lagsurf", "laglatq", "lagsatex",
    "wet_evap", "wet_oflo", "wet_stor",
)  # fmt: skip


def parse_basin_wb_aa(path: Path) -> pd.DataFrame:
    """Parse ``basin_wb_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(path, core_columns=_CORE_HEADER, text_merge_col="plant_cov")
