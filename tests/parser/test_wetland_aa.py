"""Tests for ``swatplus_ai.parser.outputs.wetland_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.wetland_aa import parse_wetland_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_wetland_aa(minimal_project / "wetland_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 65
    assert "null_3" in df.columns
    assert df.iloc[0]["name"] == "wet1"


def test_parse_uru(uru_project: Path) -> None:
    df = parse_wetland_aa(uru_project / "wetland_aa.txt")
    assert len(df) > 100
    assert df["flo_in"].notna().all()


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "wetland_aa.txt"
    p.write_text("title\njday mon day WRONG\nm3 m3 m3 m3\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="missing required core"):
        parse_wetland_aa(p)
