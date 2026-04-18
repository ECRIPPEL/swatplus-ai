"""Tests for ``swatplus_ai.parser.outputs.basin_ls_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.basin_ls_aa import parse_basin_ls_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_basin_ls_aa(minimal_project / "basin_ls_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 22
    assert df.iloc[0]["sedyld"] == pytest.approx(1.25)
    assert df.iloc[0]["plant_cov"] == "Original Simulation"


def test_parse_uru(uru_project: Path) -> None:
    df = parse_basin_ls_aa(uru_project / "basin_ls_aa.txt")
    assert len(df) >= 1
    assert df["sedyld"].iloc[0] >= 0


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "basin_ls_aa.txt"
    p.write_text("title\njday mon day WRONG\nmm mm mm mm\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="expected header"):
        parse_basin_ls_aa(p)
