"""Parser for ``pesticide.pes`` — SWAT+ pesticide-property database.

One row per pesticide (e.g. ``245-tp``, ``2plus2``), referenced from
``pest_apply`` scheduled-ops. Thirteen float columns describe soil
adsorption, wash-off fractions, foliage/soil half-lives, solubility,
aquatic fate (half-life, volatilisation, resuspension, settling,
benthic deposition/burial/half-life), and molecular weight. Trailing
``description`` is a free-text label.
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
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)


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
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[PesticidePesRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return PesticidePes(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> PesticidePesRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens "
            f"(name + {len(_FLOAT_FIELDS)} floats), got {len(line.tokens)}",
        )
    name, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return PesticidePesRow(name=name, description=description, **values)
