"""Parser for ``print.prt`` — SWAT+ output-printing configuration.

``print.prt`` controls which SWAT+ output files are written and at what time
aggregation (daily / monthly / yearly / annual-average). The file has a
fixed sequence of four small header/value blocks followed by an ``objects``
table with one row per output object.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    expect_tokens_any,
    parse_int_row,
    parse_yn,
    parse_yn_row,
)
from swatplus_ai.parser.models import ParsedFile

_PERIOD_HEADER = ("nyskip", "day_start", "yrc_start", "day_end", "yrc_end", "interval")
_AA_HEADER = ("aa_int_cnt",)
_CSVOUT_HEADER = ("csvout", "dbout", "cdfout")
_SOILOUT_HEADER = ("soilout", "mgtout", "hydcon", "fdcout")
# SWAT+ Editor v3.0+ (rev.61.0.1 / rev.61.0.2) writes ``crop_yld`` in column 1
# where SWAT+ Toolbox writes ``soilout``. Same section, different writer.
# Canonical field name stays ``soilout`` — we only widen the header check.
_SOILOUT_HEADER_ALIASES: tuple[tuple[str, ...], ...] = (
    _SOILOUT_HEADER,
    ("crop_yld", "mgtout", "hydcon", "fdcout"),
)
# Fortran ``basin_module.f90`` declares column 1 as a single character with
# valid values ``a|y|b|n`` (a=average annual, y=yearly, b=both, n=none). The
# Toolbox docs' y/n-only claim was wrong — confirmed via source, so all four
# are accepted here. Anything truthy (a/y/b) flips the boolean.
_CROP_YLD_VALID = frozenset({"a", "y", "b", "n"})
_OBJECTS_HEADER = ("objects", "daily", "monthly", "yearly", "avann")


class ObjectPrintFlags(BaseModel):
    """Per-object print flags (one row in the ``objects`` section of print.prt)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    daily: bool
    monthly: bool
    yearly: bool
    avann: bool


class PrintPrt(ParsedFile):
    """Contents of a ``print.prt`` file."""

    nyskip: int = Field(ge=0, description="Number of warm-up years to skip from output")
    day_start: int = Field(ge=0, le=366)
    yrc_start: int
    day_end: int = Field(ge=0, le=366)
    yrc_end: int
    interval: int = Field(ge=0)

    aa_int_cnt: int = Field(ge=0)

    csvout: bool
    dbout: bool
    cdfout: bool

    soilout: bool
    mgtout: bool
    hydcon: bool
    fdcout: bool

    objects: tuple[ObjectPrintFlags, ...]


def parse_print_prt(path: Path) -> PrintPrt:
    """Parse a ``print.prt`` file into a :class:`PrintPrt` model."""
    reader = LineReader(path)
    title = reader.next().text

    expect_tokens(reader.next(), _PERIOD_HEADER, path=path)
    period = parse_int_row(reader.next(), _PERIOD_HEADER, path=path)

    expect_tokens(reader.next(), _AA_HEADER, path=path)
    aa = parse_int_row(reader.next(), _AA_HEADER, path=path)

    expect_tokens(reader.next(), _CSVOUT_HEADER, path=path)
    csv_flags = parse_yn_row(reader.next(), _CSVOUT_HEADER, path=path)

    expect_tokens_any(reader.next(), _SOILOUT_HEADER_ALIASES, path=path)
    soil_flags = _parse_soilout_row(reader.next(), path=path)

    expect_tokens(reader.next(), _OBJECTS_HEADER, path=path)

    objects: list[ObjectPrintFlags] = []
    while not reader.eof():
        objects.append(_parse_object_row(reader.next(), path=path))

    return PrintPrt(
        source_path=path,
        title=title,
        **period,
        **aa,
        **csv_flags,
        **soil_flags,
        objects=tuple(objects),
    )


def _parse_soilout_row(line: Line, *, path: Path) -> dict[str, bool]:
    """Parse the soilout/crop_yld value row.

    Fortran canonical (``basin_module.f90``) accepts ``a|y|b|n`` in column 1
    (average annual / yearly / both / none). Anything truthy maps to ``True``;
    ``n`` is the only falsey value. The other three columns are strict y/n —
    anything else there still raises.
    """
    if len(line.tokens) != len(_SOILOUT_HEADER):
        raise ParseError(
            path,
            line.line_no,
            f"expected {len(_SOILOUT_HEADER)} values, got {len(line.tokens)}",
        )
    raw = line.tokens[0].strip().lower()
    if raw not in _CROP_YLD_VALID:
        raise ParseError(
            path,
            line.line_no,
            f"expected one of 'a', 'y', 'b', 'n' for 'soilout', got {line.tokens[0]!r}",
        )
    flags: dict[str, bool] = {"soilout": raw != "n"}
    for name, tok in zip(_SOILOUT_HEADER[1:], line.tokens[1:], strict=True):
        flags[name] = parse_yn(tok, path=path, line_no=line.line_no, field=name)
    return flags


def _parse_object_row(line: Line, *, path: Path) -> ObjectPrintFlags:
    if len(line.tokens) != 5:
        raise ParseError(
            path,
            line.line_no,
            f"expected 5 tokens in objects row (name + 4 flags), got {len(line.tokens)}",
        )
    name, daily_s, monthly_s, yearly_s, avann_s = line.tokens
    return ObjectPrintFlags(
        name=name,
        daily=parse_yn(daily_s, path=path, line_no=line.line_no, field=f"{name}.daily"),
        monthly=parse_yn(monthly_s, path=path, line_no=line.line_no, field=f"{name}.monthly"),
        yearly=parse_yn(yearly_s, path=path, line_no=line.line_no, field=f"{name}.yearly"),
        avann=parse_yn(avann_s, path=path, line_no=line.line_no, field=f"{name}.avann"),
    )
