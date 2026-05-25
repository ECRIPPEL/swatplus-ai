"""Tests for ``swatplus_ai.parser.outputs.basin_wb_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.diagnostics.drift import DriftRegistry
from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.basin_wb_aa import parse_basin_wb_aa

_CORE_HEADER = (
    "jday mon day yr unit gis_id name "
    "precip snofall snomlt surq_gen latq wateryld perc "
    "et ecanopy eplant esoil surq_cont cn "
    "sw_init sw_final sw_ave sw_300 sno_init sno_final snopack "
    "pet qtile irr surq_runon latq_runon overbank "
    "surq_cha surq_res surq_ls latq_cha latq_res latq_ls "
    "gwsoilq satex satex_chan sw_change "
    "lagsurf laglatq lagsatex "
    "wet_evap wet_oflo wet_stor"
)

_UNIT_LINE = " ".join(["mm"] * 42)
_CORE_VALUES = " ".join(["0.1"] * 42)


def _core_only_file(tmp_path: Path) -> Path:
    p = tmp_path / "basin_wb_aa.txt"
    p.write_text(
        "title line\n"
        f"{_CORE_HEADER}\n"
        f"---   mo  d   yr  -    -     -    {_UNIT_LINE}\n"
        f"  365  12  31  1989 1    1     basin {_CORE_VALUES}\n"
    )
    return p


def test_parse_minimal_with_suffix_present(minimal_project: Path) -> None:
    df = parse_basin_wb_aa(minimal_project / "basin_wb_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 51

    row = df.iloc[0]
    assert row["name"] == "basin"
    assert row["precip"] == pytest.approx(1200.0)
    # The fixture row ends in the Fortran-emitted scenario block
    # ``Original Simulation 0.0``. Post-stripper, plant_cov / mgt_ops
    # come through NaN because the basin-scale writer skipped them.
    assert row["plant_cov"] is None
    assert df.attrs["source_path"].endswith("basin_wb_aa.txt")
    assert df.attrs["title"].strip().startswith("synthetic_basin")


def test_parse_uru(uru_project: Path) -> None:
    df = parse_basin_wb_aa(uru_project / "basin_wb_aa.txt")
    assert len(df) >= 1
    # Real URU basin row has no per-HRU plant_cov at basin scope — the
    # stripper peels the scenario metadata and leaves it NaN.
    assert df.iloc[0]["plant_cov"] is None
    assert df["precip"].iloc[0] > 0


def test_core_only_header_parses_without_suffix(tmp_path: Path) -> None:
    """Basin runs with plant-growth off legitimately omit plant_cov / mgt_ops."""
    df = parse_basin_wb_aa(_core_only_file(tmp_path))
    assert len(df) == 1
    assert len(df.columns) == 49  # 7 metadata + 42 physical
    assert "plant_cov" not in df.columns
    assert "mgt_ops" not in df.columns
    assert df.iloc[0]["name"] == "basin"
    assert df.iloc[0]["precip"] == pytest.approx(0.1)


def test_core_only_header_does_not_emit_drift(tmp_path: Path) -> None:
    """Absence of module-conditional suffix must NOT be recorded as drift."""
    path = _core_only_file(tmp_path)
    with DriftRegistry() as reg:
        parse_basin_wb_aa(path)
    assert reg.all() == ()


def test_broken_core_prefix_raises(tmp_path: Path) -> None:
    # Header with the right number of tokens but the first column
    # renamed — should fail at the core-prefix comparison, not via
    # length.
    wrong_header = _CORE_HEADER.replace("jday", "NOTJDAY", 1)
    p = tmp_path / "basin_wb_aa.txt"
    p.write_text(
        "title line\n"
        f"{wrong_header}\n"
        f"---   mo  d   yr  -    -     -    {_UNIT_LINE}\n"
        f"  365  12  31  1989 1    1     basin {_CORE_VALUES}\n"
    )
    with pytest.raises(OutputParseError, match="missing required core"):
        parse_basin_wb_aa(p)


def test_short_header_raises(tmp_path: Path) -> None:
    # A header that doesn't carry all seven row-identifier columns
    # (``jday``..``name``) is unrecognizable as a SWAT+ output — the
    # strict_core check in ``map_columns_by_name`` raises before the
    # individual physical fields are even consulted.
    p = tmp_path / "basin_wb_aa.txt"
    p.write_text("title line\njday mon day WRONG\nmm mm mm mm\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="missing required core"):
        parse_basin_wb_aa(p)
