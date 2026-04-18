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


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    # Build a file with a correct header but a short data row.
    from swatplus_ai.parser.outputs.channel_sd_aa import _COLUMNS

    p = tmp_path / "channel_sd_aa.txt"
    short_row = " ".join(["0"] * (len(_COLUMNS) + 2))  # too many, no merge col
    content = (
        "title line\n"
        + " ".join(_COLUMNS)
        + "\n"
        + " ".join(["-"] * len(_COLUMNS))
        + "\n"
        + short_row
        + "\n"
    )
    p.write_text(content)
    with pytest.raises(OutputParseError, match="no text-merge column"):
        parse_channel_sd_aa(p)
