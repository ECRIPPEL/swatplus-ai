"""Parser for ``topography.hyd`` — SWAT+ per-landscape-object topography.

One row per HRU or routing-unit (names like ``topohru00001`` /
``toportu2102``). Five float columns drive overland-flow length,
lateral-flow length, channel distance, and deposition:

- ``slp`` — average slope (m/m) — classic calibration knob
- ``slp_len`` — average slope length (m)
- ``lat_len`` — lateral-flow path length (m)
- ``dist_cha`` — average distance from field to channel (m)
- ``depos`` — deposition fraction (unitless)

Physical-range validation (e.g. slope in [0, 1]) is deferred to the
diagnostic-rule engine.
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
    "slp",
    "slp_len",
    "lat_len",
    "dist_cha",
    "depos",
)

_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS)


class TopographyHydRow(BaseModel):
    """Topography parameters for a single HRU or routing unit."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    slp: float
    slp_len: float
    lat_len: float
    dist_cha: float
    depos: float


class TopographyHyd(ParsedFile):
    """Contents of a ``topography.hyd`` file: one row per HRU/routing unit."""

    rows: tuple[TopographyHydRow, ...]

    def by_name(self, name: str) -> TopographyHydRow | None:
        """Linear lookup by topography-parameter-set name. O(n); cache if hot."""
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_topography_hyd(path: Path) -> TopographyHyd:
    """Parse a ``topography.hyd`` file into a :class:`TopographyHyd` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[TopographyHydRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    return TopographyHyd(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> TopographyHydRow:
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
    return TopographyHydRow(name=name, **values)
