"""Tests for ``swatplus_ai.parser.outputs.hru_pw_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.hru_pw_aa import parse_hru_pw_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_hru_pw_aa(minimal_project / "hru_pw_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert len(df.columns) == 34
    assert df["lai"].iloc[0] == pytest.approx(2.5)


def test_parse_uru(uru_project: Path) -> None:
    df = parse_hru_pw_aa(uru_project / "hru_pw_aa.txt")
    assert len(df) > 10_000
    assert df["tmpav"].notna().all()


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "hru_pw_aa.txt"
    p.write_text("title\njday mon day WRONG\nunit unit unit unit\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="expected header"):
        parse_hru_pw_aa(p)
