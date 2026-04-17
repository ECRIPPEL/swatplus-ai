"""Parser for ``hyd-sed-lte.cha`` — channel hydrology + sediment parameters.

One row per named parameter set referenced from ``channel-lte.cha``'s
``cha_hyd`` column. Flat 23-column shape: ``name``, ``order`` (int),
21 float parameters covering channel geometry (width, depth, slope,
length, sinuosity), roughness (Manning's n), erodibility, bed/bank
composition, and floodplain coefficients. An optional trailing
``description`` column may be present.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_float,
    parse_int,
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = (
    "wd",
    "dp",
    "slp",
    "len",
    "mann",
    "k",
    "erod_fact",
    "cov_fact",
    "sinu",
    "eq_slp",
    "d50",
    "clay",
    "carbon",
    "dry_bd",
    "side_slp",
    "bankfull_flo",
    "fps",
    "fpn",
    "n_conc",
    "p_conc",
    "p_bio",
)
_HEADER: tuple[str, ...] = ("name", "order", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 2 + len(_FLOAT_FIELDS)  # name + order + 21 floats; description optional.


class HydSedLteChaRow(BaseModel):
    """Channel hydrology + sediment parameters for one named set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    order: int
    wd: float
    dp: float
    slp: float
    len: float
    mann: float
    k: float
    erod_fact: float
    cov_fact: float
    sinu: float
    eq_slp: float
    d50: float
    clay: float
    carbon: float
    dry_bd: float
    side_slp: float
    bankfull_flo: float
    fps: float
    fpn: float
    n_conc: float
    p_conc: float
    p_bio: float
    description: str | None


class HydSedLteCha(ParsedFile):
    """Contents of a ``hyd-sed-lte.cha`` file."""

    rows: tuple[HydSedLteChaRow, ...]

    def by_name(self, name: str) -> HydSedLteChaRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_hyd_sed_lte_cha(path: Path) -> HydSedLteCha:
    """Parse a ``hyd-sed-lte.cha`` file into a :class:`HydSedLteCha` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HydSedLteChaRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return HydSedLteCha(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HydSedLteChaRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens (name order + {len(_FLOAT_FIELDS)} floats), "
            f"got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    order = parse_int(line.tokens[1], path=path, line_no=ln, field="order")
    float_toks = line.tokens[2 : 2 + len(_FLOAT_FIELDS)]
    desc_toks = line.tokens[2 + len(_FLOAT_FIELDS) :]
    float_values = {
        field: parse_float(tok, path=path, line_no=ln, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return HydSedLteChaRow(name=name, order=order, description=description, **float_values)
