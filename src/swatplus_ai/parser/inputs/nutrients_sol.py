"""Parser for ``nutrients.sol`` — SWAT+ soil nutrient parameter database.

One row per named soil-nutrient parameter set (e.g. ``soilnut1``),
referenced from ``soils.sol``. Eleven float columns describe how
nitrogen, phosphorus, and their organic/mineral/soluble pools are
partitioned, plus a ``dp_co`` decay-profile coefficient. The 13th
header column ``description`` is a free-text trailing field — often
blank, sometimes a multi-word label — which we preserve as an
optional string.

Physical bounds (fractions in [0, 1], tot_n > min_n + org_n, etc.)
are enforced by the diagnostic-rule engine, not here.
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
    "dp_co",
    "tot_n",
    "min_n",
    "org_n",
    "tot_p",
    "min_p",
    "org_p",
    "sol_p",
    "h3a_p",
    "mehl_p",
    "bray_p",
)

_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)  # name + 11 floats; description optional.


class NutrientsSolRow(BaseModel):
    """Soil nutrient parameters for a single named parameter set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    dp_co: float
    tot_n: float
    min_n: float
    org_n: float
    tot_p: float
    min_p: float
    org_p: float
    sol_p: float
    h3a_p: float
    mehl_p: float
    bray_p: float
    description: str | None


class NutrientsSol(ParsedFile):
    """Contents of a ``nutrients.sol`` file: one row per nutrient parameter set."""

    rows: tuple[NutrientsSolRow, ...]

    def by_name(self, name: str) -> NutrientsSolRow | None:
        """Linear lookup by nutrient-set name. O(n); cache if hot."""
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_nutrients_sol(path: Path) -> NutrientsSol:
    """Parse a ``nutrients.sol`` file into a :class:`NutrientsSol` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[NutrientsSolRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))

    return NutrientsSol(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> NutrientsSolRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens (name + {len(_FLOAT_FIELDS)} floats), "
            f"got {len(line.tokens)}",
        )
    name, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]

    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return NutrientsSolRow(name=name, description=description, **values)
