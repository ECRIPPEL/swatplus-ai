"""Parser for ``hru_wb_aa.txt`` — per-HRU annual-average water balance.

Same core schema as :mod:`basin_wb_aa` but one data row per HRU; URU
ships ~12,500 rows. At HRU scope ``plant_cov`` and ``mgt_ops`` carry
each HRU's assigned land-use code and management schedule, so they are
almost always present. The variable-suffix reader accepts files where
those labels are omitted for completeness — if the user wires this
parser at basin scope by mistake, it still reads cleanly instead of
crashing. Multi-word merging for ``plant_cov`` stays on defensively
even though HRU scope emits single-word codes.
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


def parse_hru_wb_aa(path: Path) -> pd.DataFrame:
    """Parse ``hru_wb_aa.txt`` into a DataFrame."""
    return read_aa_output_variable(path, core_columns=_CORE_HEADER, text_merge_col="plant_cov")
