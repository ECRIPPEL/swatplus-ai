"""Tests for ``swatplus_ai.parser.outputs.hru_nb_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.hru_nb_aa import parse_hru_nb_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_hru_nb_aa(minimal_project / "hru_nb_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert len(df.columns) == 28


def test_parse_uru(uru_project: Path) -> None:
    df = parse_hru_nb_aa(uru_project / "hru_nb_aa.txt")
    assert len(df) > 10_000
    assert df["denit"].notna().all()


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "hru_nb_aa.txt"
    p.write_text("title\njday mon day WRONG\nkg kg kg kg\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="expected header"):
        parse_hru_nb_aa(p)
