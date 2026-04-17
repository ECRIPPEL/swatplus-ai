"""Parser for ``nutrients.cha`` — SWAT+ channel nutrient-cycling parameters.

One row per named parameter set referenced from ``channel-lte.cha``'s
``cha_nut`` column. Very wide shape: 38 numeric columns covering in-stream
algal growth, settling, organic/mineral nitrogen and phosphorus cycling,
BOD decay and reaeration, and bacterial die-off. An optional trailing
``description`` column may be present.

Two columns in the middle (``q2e_lt``, ``q2e_alg``) are integer-coded
method flags in practice but written as plain numbers — we parse every
column as float to sidestep writer variation; the diagnostic engine is
the right place to enforce integrality.
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
    "plt_n",
    "ptl_p",
    "alg_stl",
    "ben_disp",
    "ben_nh3n",
    "ptln_stl",
    "ptlp_stl",
    "cst_stl",
    "ben_cst",
    "cbn_bod_co",
    "air_rt",
    "cbn_bod_stl",
    "ben_bod",
    "bact_die",
    "cst_decay",
    "nh3n_no2n",
    "no2n_no3n",
    "ptln_nh3n",
    "ptlp_solp",
    "q2e_lt",
    "q2e_alg",
    "chla_alg",
    "alg_n",
    "alg_p",
    "alg_o2_prod",
    "alg_o2_resp",
    "o2_nh3n",
    "o2_no2n",
    "alg_grow",
    "alg_resp",
    "slr_act",
    "lt_co",
    "const_n",
    "const_p",
    "lt_nonalg",
    "alg_shd_l",
    "alg_shd_nl",
    "nh3_pref",
)
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)  # name + 38 floats; description optional.


class NutrientsChaRow(BaseModel):
    """Channel nutrient parameters for one named set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    plt_n: float
    ptl_p: float
    alg_stl: float
    ben_disp: float
    ben_nh3n: float
    ptln_stl: float
    ptlp_stl: float
    cst_stl: float
    ben_cst: float
    cbn_bod_co: float
    air_rt: float
    cbn_bod_stl: float
    ben_bod: float
    bact_die: float
    cst_decay: float
    nh3n_no2n: float
    no2n_no3n: float
    ptln_nh3n: float
    ptlp_solp: float
    q2e_lt: float
    q2e_alg: float
    chla_alg: float
    alg_n: float
    alg_p: float
    alg_o2_prod: float
    alg_o2_resp: float
    o2_nh3n: float
    o2_no2n: float
    alg_grow: float
    alg_resp: float
    slr_act: float
    lt_co: float
    const_n: float
    const_p: float
    lt_nonalg: float
    alg_shd_l: float
    alg_shd_nl: float
    nh3_pref: float
    description: str | None


class NutrientsCha(ParsedFile):
    """Contents of a ``nutrients.cha`` file."""

    rows: tuple[NutrientsChaRow, ...]

    def by_name(self, name: str) -> NutrientsChaRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_nutrients_cha(path: Path) -> NutrientsCha:
    """Parse a ``nutrients.cha`` file into a :class:`NutrientsCha` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[NutrientsChaRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return NutrientsCha(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> NutrientsChaRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens (name + {len(_FLOAT_FIELDS)} floats), "
            f"got {len(line.tokens)}",
        )
    ln = line.line_no
    name = line.tokens[0]
    float_toks = line.tokens[1 : 1 + len(_FLOAT_FIELDS)]
    desc_toks = line.tokens[1 + len(_FLOAT_FIELDS) :]
    float_values = {
        field: parse_float(tok, path=path, line_no=ln, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return NutrientsChaRow(name=name, description=description, **float_values)
