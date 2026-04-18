"""Tests for ``swatplus_ai.parser.outputs.aquifer_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.aquifer_aa import parse_aquifer_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_aquifer_aa(minimal_project / "aquifer_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 24
    assert df.iloc[0]["name"] == "aqu1"
    assert df.iloc[0]["flo"] == pytest.approx(25.0)


def test_parse_uru(uru_project: Path) -> None:
    df = parse_aquifer_aa(uru_project / "aquifer_aa.txt")
    assert len(df) > 10
    assert df["dep_wt"].notna().all()


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "aquifer_aa.txt"
    p.write_text("title\njday mon day WRONG\nmm mm mm mm\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="expected header"):
        parse_aquifer_aa(p)
