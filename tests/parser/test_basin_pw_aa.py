"""Tests for ``swatplus_ai.parser.outputs.basin_pw_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.basin_pw_aa import parse_basin_pw_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_basin_pw_aa(minimal_project / "basin_pw_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 34
    assert df.iloc[0]["lai"] == pytest.approx(2.5)
    # Basin scope: stripper peels the scenario block so plant_cov
    # (declared but not emitted by the writer) comes through NaN.
    assert df.iloc[0]["plant_cov"] is None


def test_parse_uru(uru_project: Path) -> None:
    df = parse_basin_pw_aa(uru_project / "basin_pw_aa.txt")
    assert len(df) >= 1
    assert df["bioms"].iloc[0] >= 0


def test_short_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "basin_pw_aa.txt"
    p.write_text("only one line\n")
    with pytest.raises(OutputParseError, match="at least 3"):
        parse_basin_pw_aa(p)
