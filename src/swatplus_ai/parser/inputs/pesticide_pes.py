"""Parser for ``pesticide.pes`` — SWAT+ pesticide-property database.

One row per pesticide (e.g. ``245-tp``, ``2plus2``), referenced from
``pest_apply`` scheduled-ops. Thirteen float columns describe soil
adsorption, wash-off fractions, foliage/soil half-lives, solubility,
aquatic fate (half-life, volatilisation, resuspension, settling,
benthic deposition/burial/half-life), and molecular weight. Trailing
``description`` is a free-text label.

Header reading is permissive: SWAT+ Editor has historically grown the
column set (rev.61.x projects observed in dogfood carry an extra
``pl_uptake`` column between ``ben_hlife`` and ``description`` that
our baseline doesn't know about). Extra columns are recorded as
``unknown_column`` drifts and skipped at row-read time so known
columns still map to the right fields.
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

_FLOAT_FIELDS: tuple[str, ...] = (
    "soil_ads",
    "frac_wash",
    "hl_foliage",
    "hl_soil",
    "solub",
    "aq_hlife",
    "aq_volat",
    "mol_wt",
    "aq_resus",
    "aq_settle",
    "ben_act_dep",
    "ben_bury",
    "ben_hlife",
)
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_FILE = "pesticide.pes"


class PesticidePesRow(BaseModel):
    """Parameters for a single pesticide."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    soil_ads: float
    frac_wash: float
    hl_foliage: float
    hl_soil: float
    solub: float
    aq_hlife: float
    aq_volat: float
    mol_wt: float
    aq_resus: float
    aq_settle: float
    ben_act_dep: float
    ben_bury: float
    ben_hlife: float
    description: str | None


class PesticidePes(ParsedFile):
    """Contents of a ``pesticide.pes`` file."""

    rows: tuple[PesticidePesRow, ...]

    def by_name(self, name: str) -> PesticidePesRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_pesticide_pes(path: Path) -> PesticidePes:
    """Parse a ``pesticide.pes`` file into a :class:`PesticidePes` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[PesticidePesRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return PesticidePes(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> PesticidePesRow:
    desc_start = idx_map["description"]
    # Required columns are everything up to (not including) description;
    # description itself is optional (multi-word trailer allowed).
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
    return PesticidePesRow(name=name, description=description, **values)
