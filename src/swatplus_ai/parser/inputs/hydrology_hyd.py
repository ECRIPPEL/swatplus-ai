"""Parser for ``hydrology.hyd`` — SWAT+ per-HRU hydrology parameters.

One row per HRU. The first token is the HRU's hydrology-parameter-set name
(e.g. ``hyd00001``) which is referenced from ``hru-data.hru``; the remaining
14 tokens are the hydrology parameters that drive runoff, infiltration,
canopy storage, percolation, and lateral flow.

The parser loads and types every row but does *not* enforce physical
ranges here — checks like "esco must be in [0, 1]" belong in the
diagnostic-rule engine, where they can carry severity, literature
citations, and user-facing guidance.
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
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = (
    "lat_ttime",  # lateral flow travel time [days]
    "lat_sed",  # lateral sediment concentration [mg/L]
    "can_max",  # maximum canopy storage [mm]
    "esco",  # soil evaporation compensation factor [0-1]
    "epco",  # plant uptake compensation factor [0-1]
    "orgn_enrich",  # organic N enrichment ratio
    "orgp_enrich",  # organic P enrichment ratio
    "cn3_swf",  # CN3 soil water factor
    "bio_mix",  # biological mixing efficiency [0-1]
    "perco",  # percolation coefficient [0-1]
    "lat_orgn",  # lateral flow organic N concentration
    "lat_orgp",  # lateral flow organic P concentration
    "pet_co",  # PET coefficient
    "latq_co",  # lateral flow coefficient
)

_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS)


class HydrologyHydRow(BaseModel):
    """Hydrology parameters for a single HRU (one row of hydrology.hyd)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str

    lat_ttime: float
    lat_sed: float
    can_max: float
    esco: float
    epco: float
    orgn_enrich: float
    orgp_enrich: float
    cn3_swf: float
    bio_mix: float
    perco: float
    lat_orgn: float
    lat_orgp: float
    pet_co: float
    latq_co: float


class HydrologyHyd(ParsedFile):
    """Contents of a ``hydrology.hyd`` file: one row per HRU."""

    rows: tuple[HydrologyHydRow, ...]

    def by_name(self, name: str) -> HydrologyHydRow | None:
        """Linear lookup by HRU parameter-set name. O(n); cache if hot."""
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_hydrology_hyd(path: Path) -> HydrologyHyd:
    """Parse a ``hydrology.hyd`` file into a :class:`HydrologyHyd` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[HydrologyHydRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    return HydrologyHyd(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> HydrologyHydRow:
    expected = len(_HEADER)
    if len(line.tokens) != expected:
        raise ParseError(
            path,
            line.line_no,
            f"expected {expected} tokens (name + {len(_FLOAT_FIELDS)} floats), "
            f"got {len(line.tokens)}",
        )
    name, *value_toks = line.tokens
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, value_toks, strict=True)
    }
    return HydrologyHydRow(name=name, **values)
