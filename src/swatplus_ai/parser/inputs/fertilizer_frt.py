"""Parser for ``fertilizer.frt`` — SWAT+ fertilizer / manure parameter DB.

One row per named fertilizer or manure product (e.g. ``urea``,
``dairy_fr``), referenced from management operations (the
``fertilize`` / ``fertilizr`` scheduled op in ``management.sch``
uses ``op_data1`` to look up a row here).

Columns:
- ``name`` — product name (key)
- ``min_n, min_p`` — mineral N/P mass fraction
- ``org_n, org_p`` — organic N/P mass fraction
- ``nh3_n`` — ammonia fraction of mineral N
- ``pathogens`` — pathogen class name (nullable; written as ``null`` for
  non-manure products)
- ``description`` — free-text label (optional trailing tokens)

Physical-range checks (fractions in [0, 1], mass balance) belong in the
diagnostic-rule engine.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_header_permissive,
    parse_float,
    parse_nullable_str,
    record_unknown_columns,
)
from swatplus_ai.parser.models import ParsedFile

_FLOAT_FIELDS: tuple[str, ...] = (
    "min_n",
    "min_p",
    "org_n",
    "org_p",
    "nh3_n",
)

_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "pathogens", "description")
_FILE = "fertilizer.frt"


class FertilizerFrtRow(BaseModel):
    """Parameters for a single fertilizer / manure product."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    min_n: float
    min_p: float
    org_n: float
    org_p: float
    nh3_n: float
    pathogens: str | None
    description: str | None


class FertilizerFrt(ParsedFile):
    """Contents of a ``fertilizer.frt`` file: one row per product."""

    rows: tuple[FertilizerFrtRow, ...]

    def by_name(self, name: str) -> FertilizerFrtRow | None:
        """Linear lookup by product name. O(n); cache if hot."""
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_fertilizer_frt(path: Path) -> FertilizerFrt:
    """Parse a ``fertilizer.frt`` file into a :class:`FertilizerFrt` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[FertilizerFrtRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return FertilizerFrt(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> FertilizerFrtRow:
    desc_start = idx_map["description"]
    if len(line.tokens) < desc_start:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {desc_start} tokens before 'description', got {len(line.tokens)}",
        )
    tokens = line.tokens
    ln = line.line_no
    name = tokens[idx_map["name"]]
    pathogens_tok = tokens[idx_map["pathogens"]]
    values = {
        field: parse_float(tokens[idx_map[field]], path=path, line_no=ln, field=field)
        for field in _FLOAT_FIELDS
    }
    desc_toks = tokens[desc_start:]
    description = " ".join(desc_toks) if desc_toks else None
    return FertilizerFrtRow(
        name=name,
        pathogens=parse_nullable_str(pathogens_tok),
        description=description,
        **values,
    )
