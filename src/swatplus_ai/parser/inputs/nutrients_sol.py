"""Parser for ``nutrients.sol`` — SWAT+ soil-test nutrient database.

Schema is the Fortran ``soiltest_db`` type (``src/soil_data_module.f90``
in ``swat-model/swatplus``) read by ``solt_db_read.f90``: one row per
named soil-test parameter set, eleven real columns plus a free-text
``description`` trailer. The Fortran reader uses list-directed I/O and
does **not** validate column names — they're documentation only — so
the header row is effectively a label for the writer's benefit.

Historical note: the original 7.3 parser mapped this file against an
outdated SWAT+ Toolbox baseline (``dp_co, tot_n, min_n, ...``). Source
consultation for slice 7.3g confirmed the Fortran canonical schema is
the one SWAT+ Editor v3.x writes verbatim, so the parser now aligns
with Fortran and the Toolbox-baseline fixture was regenerated to match.

Physical bounds (positive concentrations, C:N / C:P ratio ranges) are
enforced by the diagnostic-rule engine, not here.
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
    record_unknown_columns,
)
from swatplus_ai.parser.models import ParsedFile

# Field order must match ``type soiltest_db`` in ``swat-model/swatplus``
# ``src/soil_data_module.f90`` — the Fortran reader reads positionally,
# so any rearrangement silently mis-assigns values.
_FLOAT_FIELDS: tuple[str, ...] = (
    "exp_co",
    "lab_p",
    "nitrate",
    "fr_hum_act",
    "hum_c_n",
    "hum_c_p",
    "inorgp",
    "watersol_p",
    "h3a_p",
    "mehlich_p",
    "bray_strong_p",
)

_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_FILE = "nutrients.sol"


class NutrientsSolRow(BaseModel):
    """Soil-test nutrient parameters for a single named set.

    Field names and order mirror the Fortran ``soiltest_db`` type.
    ``description`` is free text and optional — many real rows omit it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    exp_co: float
    lab_p: float
    nitrate: float
    fr_hum_act: float
    hum_c_n: float
    hum_c_p: float
    inorgp: float
    watersol_p: float
    h3a_p: float
    mehlich_p: float
    bray_strong_p: float
    description: str | None


class NutrientsSol(ParsedFile):
    """Contents of a ``nutrients.sol`` file: one row per soil-test set."""

    rows: tuple[NutrientsSolRow, ...]

    def by_name(self, name: str) -> NutrientsSolRow | None:
        """Linear lookup by set name. O(n); cache if hot."""
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_nutrients_sol(path: Path) -> NutrientsSol:
    """Parse a ``nutrients.sol`` file into a :class:`NutrientsSol` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[NutrientsSolRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return NutrientsSol(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> NutrientsSolRow:
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
    values = {
        field: parse_float(tokens[idx_map[field]], path=path, line_no=ln, field=field)
        for field in _FLOAT_FIELDS
    }
    desc_toks = tokens[desc_start:]
    description = " ".join(desc_toks) if desc_toks else None
    return NutrientsSolRow(name=name, description=description, **values)
