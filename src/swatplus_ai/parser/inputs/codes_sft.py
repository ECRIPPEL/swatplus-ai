"""Parser for ``codes.sft`` — soft-calibration enable flags.

Single-row file: title line, then a header of 8 module names
(``hyd landscape plnt sed nut ch_sed ch_nut res``), then a single
row of 8 y/n flags indicating whether that module participates in
soft calibration.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict

from swatplus_ai.parser._base import (
    LineReader,
    expect_tokens,
    parse_yn_row,
)
from swatplus_ai.parser.models import ParsedFile

_FIELDS: tuple[str, ...] = (
    "hyd",
    "landscape",
    "plnt",
    "sed",
    "nut",
    "ch_sed",
    "ch_nut",
    "res",
)


class CodesSft(ParsedFile):
    """Contents of a ``codes.sft`` file — one flag per soft-cal module."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hyd: bool
    landscape: bool
    plnt: bool
    sed: bool
    nut: bool
    ch_sed: bool
    ch_nut: bool
    res: bool


def parse_codes_sft(path: Path) -> CodesSft:
    """Parse a ``codes.sft`` file into a :class:`CodesSft` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _FIELDS, path=path)
    values = parse_yn_row(reader.next(), _FIELDS, path=path)
    return CodesSft(source_path=path, title=title, **values)
