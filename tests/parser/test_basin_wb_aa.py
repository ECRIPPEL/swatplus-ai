"""Tests for ``swatplus_ai.parser.outputs.basin_wb_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.basin_wb_aa import parse_basin_wb_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_basin_wb_aa(minimal_project / "basin_wb_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 51

    row = df.iloc[0]
    assert row["name"] == "basin"
    assert row["precip"] == pytest.approx(1200.0)
    assert row["plant_cov"] == "Original Simulation"
    assert df.attrs["source_path"].endswith("basin_wb_aa.txt")
    assert df.attrs["title"].strip().startswith("synthetic_basin")


def test_parse_uru(uru_project: Path) -> None:
    df = parse_basin_wb_aa(uru_project / "basin_wb_aa.txt")
    assert len(df) >= 1
    assert df.iloc[0]["plant_cov"] == "Original Simulation"
    assert df["precip"].iloc[0] > 0


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "basin_wb_aa.txt"
    p.write_text("title line\njday mon day WRONG\nmm mm mm mm\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="expected header"):
        parse_basin_wb_aa(p)
