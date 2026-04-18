"""Tests for ``swatplus_ai.parser.outputs.reservoir_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.reservoir_aa import parse_reservoir_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_reservoir_aa(minimal_project / "reservoir_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 65
    # Three null separators deduped to null, null_2, null_3.
    assert "null" in df.columns
    assert "null_2" in df.columns
    assert "null_3" in df.columns
    assert df.iloc[0]["name"] == "res1"


def test_parse_uru(uru_project: Path) -> None:
    df = parse_reservoir_aa(uru_project / "reservoir_aa.txt")
    assert len(df) >= 1
    assert df["flo_in"].notna().all()


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "reservoir_aa.txt"
    p.write_text("title\njday mon day WRONG\nm3 m3 m3 m3\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="expected header"):
        parse_reservoir_aa(p)
