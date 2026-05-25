"""Tests for ``swatplus_ai.parser.outputs.channel_sd_aa``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs._base import OutputParseError
from swatplus_ai.parser.outputs.channel_sd_aa import parse_channel_sd_aa


def test_parse_minimal(minimal_project: Path) -> None:
    df = parse_channel_sd_aa(minimal_project / "channel_sd_aa.txt")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    # 66 columns with three null separators deduped to null, null_2, null_3
    assert len(df.columns) == 66
    assert "null" in df.columns
    assert "null_2" in df.columns
    assert "null_3" in df.columns
    assert df.iloc[0]["flo_out"] == pytest.approx(480.0)


def test_parse_uru(uru_project: Path) -> None:
    df = parse_channel_sd_aa(uru_project / "channel_sd_aa.txt")
    assert len(df) > 100
    assert df["flo_in"].notna().all()
    assert df["flo_out"].notna().all()


def test_row_wider_than_declared_plus_trailing_raises(tmp_path: Path) -> None:
    # After the trailing-scenario stripper, a non-merge file should still
    # reject rows that remain wider than the declared schema — i.e. rows
    # with more than ``declared + expected_trailing_count`` tokens. Use
    # ``+ 4`` so that one surplus token remains after the 3-token strip.
    from swatplus_ai.parser.outputs.channel_sd_aa import _COLUMNS

    p = tmp_path / "channel_sd_aa.txt"
    wide_row = " ".join(["0"] * (len(_COLUMNS) + 4))
    content = (
        "title line\n"
        + " ".join(_COLUMNS)
        + "\n"
        + " ".join(["-"] * len(_COLUMNS))
        + "\n"
        + wide_row
        + "\n"
    )
    p.write_text(content)
    with pytest.raises(OutputParseError, match="no text-merge column"):
        parse_channel_sd_aa(p)
