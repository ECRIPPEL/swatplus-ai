"""SWAT+ output-file parsers (annual-average / yearly summaries).

This subpackage sits alongside ``parser/inputs/`` but is intentionally
different in shape: inputs are validated pydantic row-models, whereas
outputs are pandas DataFrames. The motivation is Tier A of the three-tier
output architecture described in ``swatplus-ai_architecture.md``: the
per-year / annual-average files are small (one row per basin / HRU /
channel / aquifer / reservoir / wetland) and are read eagerly into
DataFrames for downstream analysis. Per-timestep Tier B files will be
handled later via DuckDB, and Tier C streaming is for flow_duration /
hydrograph detail.

``OutputsNamespace`` bundles the DataFrames produced by the 13 Slice A
parsers and exposes a :meth:`read` constructor that tolerates missing
files — a TxtInOut folder whose simulation hasn't been run yet, or one
that only prints a subset of outputs, is still parseable.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ConfigDict

from swatplus_ai import telemetry
from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.aquifer_aa import parse_aquifer_aa
from swatplus_ai.parser.outputs.basin_ls_aa import parse_basin_ls_aa
from swatplus_ai.parser.outputs.basin_nb_aa import parse_basin_nb_aa
from swatplus_ai.parser.outputs.basin_pw_aa import parse_basin_pw_aa
from swatplus_ai.parser.outputs.basin_wb_aa import parse_basin_wb_aa
from swatplus_ai.parser.outputs.channel_sd_aa import parse_channel_sd_aa
from swatplus_ai.parser.outputs.channel_sdmorph_aa import parse_channel_sdmorph_aa
from swatplus_ai.parser.outputs.hru_ls_aa import parse_hru_ls_aa
from swatplus_ai.parser.outputs.hru_nb_aa import parse_hru_nb_aa
from swatplus_ai.parser.outputs.hru_pw_aa import parse_hru_pw_aa
from swatplus_ai.parser.outputs.hru_wb_aa import parse_hru_wb_aa
from swatplus_ai.parser.outputs.reservoir_aa import parse_reservoir_aa
from swatplus_ai.parser.outputs.wetland_aa import parse_wetland_aa


def _optional_output(
    folder: Path, name: str, parser: Callable[[Path], pd.DataFrame]
) -> pd.DataFrame | None:
    """Parse ``folder / name`` into a DataFrame if it exists, else ``None``.

    Emits a ``file_parsed`` (or ``parse_error``) telemetry event when the
    file is present. Absent optional output files stay silent — a project
    whose simulation hasn't been run shouldn't fill the log with misses.
    """
    p = folder / name
    if not p.is_file():
        return None
    t0 = time.perf_counter()
    try:
        df = parser(p)
    except Exception as exc:
        fields: dict[str, Any] = {"filename": name, "exception": type(exc).__name__}
        telemetry.emit("parse_error", **fields)
        raise
    duration_ms = round((time.perf_counter() - t0) * 1000)
    telemetry.emit(
        "file_parsed",
        filename=name,
        rows=len(df) if df is not None else None,
        duration_ms=duration_ms,
    )
    return df


class OutputsNamespace(BaseModel):
    """Annual-average / yearly output DataFrames for a TxtInOut project.

    Every field is optional: a project whose simulation has not been run
    yet, or whose ``print.prt`` suppresses a given output, will simply
    have ``None`` for the missing attributes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    folder: Path

    basin_wb_aa: pd.DataFrame | None = None
    basin_pw_aa: pd.DataFrame | None = None
    basin_ls_aa: pd.DataFrame | None = None
    basin_nb_aa: pd.DataFrame | None = None

    hru_wb_aa: pd.DataFrame | None = None
    hru_pw_aa: pd.DataFrame | None = None
    hru_ls_aa: pd.DataFrame | None = None
    hru_nb_aa: pd.DataFrame | None = None

    channel_sd_aa: pd.DataFrame | None = None
    channel_sdmorph_aa: pd.DataFrame | None = None

    aquifer_aa: pd.DataFrame | None = None
    reservoir_aa: pd.DataFrame | None = None
    wetland_aa: pd.DataFrame | None = None

    @classmethod
    def read(cls, folder: Path) -> OutputsNamespace:
        """Parse every known annual-average output file in ``folder``."""
        folder = Path(folder)
        if not folder.is_dir():
            raise NotADirectoryError(f"Outputs folder not found: {folder}")

        return cls(
            folder=folder,
            basin_wb_aa=_optional_output(folder, "basin_wb_aa.txt", parse_basin_wb_aa),
            basin_pw_aa=_optional_output(folder, "basin_pw_aa.txt", parse_basin_pw_aa),
            basin_ls_aa=_optional_output(folder, "basin_ls_aa.txt", parse_basin_ls_aa),
            basin_nb_aa=_optional_output(folder, "basin_nb_aa.txt", parse_basin_nb_aa),
            hru_wb_aa=_optional_output(folder, "hru_wb_aa.txt", parse_hru_wb_aa),
            hru_pw_aa=_optional_output(folder, "hru_pw_aa.txt", parse_hru_pw_aa),
            hru_ls_aa=_optional_output(folder, "hru_ls_aa.txt", parse_hru_ls_aa),
            hru_nb_aa=_optional_output(folder, "hru_nb_aa.txt", parse_hru_nb_aa),
            channel_sd_aa=_optional_output(folder, "channel_sd_aa.txt", parse_channel_sd_aa),
            channel_sdmorph_aa=_optional_output(
                folder, "channel_sdmorph_aa.txt", parse_channel_sdmorph_aa
            ),
            aquifer_aa=_optional_output(folder, "aquifer_aa.txt", parse_aquifer_aa),
            reservoir_aa=_optional_output(folder, "reservoir_aa.txt", parse_reservoir_aa),
            wetland_aa=_optional_output(folder, "wetland_aa.txt", parse_wetland_aa),
        )


__all__ = [
    "OutputParseError",
    "OutputsNamespace",
    "parse_aquifer_aa",
    "parse_basin_ls_aa",
    "parse_basin_nb_aa",
    "parse_basin_pw_aa",
    "parse_basin_wb_aa",
    "parse_channel_sd_aa",
    "parse_channel_sdmorph_aa",
    "parse_hru_ls_aa",
    "parse_hru_nb_aa",
    "parse_hru_pw_aa",
    "parse_hru_wb_aa",
    "parse_reservoir_aa",
    "parse_wetland_aa",
]
