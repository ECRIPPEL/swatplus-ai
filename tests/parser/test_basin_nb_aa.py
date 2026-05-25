"""Tests for ``swatplus_ai.parser.outputs.basin_nb_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.basin_nb_aa import parse_basin_nb_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_basin_nb_aa(minimal_project / "basin_nb_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 28
    assert df.iloc[0]["fertn"] == pytest.approx(20.0)
    # Basin scope: plant_cov / mgt_ops declared in header but not in row;
    # stripper peels the trailing scenario block so these come through NaN.
    assert df.iloc[0]["plant_cov"] is None


def test_parse_uru(uru_project: Path) -> None:
    df = parse_basin_nb_aa(uru_project / "basin_nb_aa.txt")
    assert len(df) >= 1
    assert df["nuptake"].iloc[0] >= 0


def test_broken_core_prefix_raises(tmp_path: Path) -> None:
    p = tmp_path / "basin_nb_aa.txt"
    p.write_text("title\njday mon day WRONG\nkg kg kg kg\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="missing required core"):
        parse_basin_nb_aa(p)
