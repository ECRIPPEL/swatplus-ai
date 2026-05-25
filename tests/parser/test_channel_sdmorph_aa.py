"""Tests for ``swatplus_ai.parser.outputs.channel_sdmorph_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.channel_sdmorph_aa import parse_channel_sdmorph_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_channel_sdmorph_aa(minimal_project / "channel_sdmorph_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 33
    # deg_btm and deg_bank appear twice; the second occurrences get _2 suffix.
    assert "deg_btm" in df.columns
    assert "deg_btm_2" in df.columns
    assert "deg_bank" in df.columns
    assert "deg_bank_2" in df.columns


def test_parse_uru(uru_project: Path) -> None:
    df = parse_channel_sdmorph_aa(uru_project / "channel_sdmorph_aa.txt")
    assert len(df) > 100
    assert df["width"].notna().all()


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "channel_sdmorph_aa.txt"
    p.write_text("title\njday mon day WRONG\nm m m m\n1 2 3 4\n")
    with pytest.raises(OutputParseError, match="missing required core"):
        parse_channel_sdmorph_aa(p)
