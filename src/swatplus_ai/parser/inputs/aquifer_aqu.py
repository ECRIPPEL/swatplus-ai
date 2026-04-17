"""Parser for ``aquifer.aqu`` — SWAT+ physical aquifer parameters.

One row per named aquifer object declared in ``aquifer.con``. The row
begins with ``id name init`` — ``init`` is a string FK into
``initial.aqu`` — followed by 15 float columns describing baseflow,
recharge, revap, specific yield, and nitrate half-life parameters.
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
    "gw_flo",
    "dep_bot",
    "dep_wt",
    "no3_n",
    "sol_p",
    "carbon",
    "flo_dist",
    "bf_max",
    "alpha_bf",
    "revap",
    "rchg_dp",
    "spec_yld",
    "hl_no3n",
    "flo_min",
    "revap_min",
)

_HEADER: tuple[str, ...] = ("id", "name", "init", *_FLOAT_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class AquiferAquRow(BaseModel):
    """Physical parameters for a single aquifer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    init: str
    gw_flo: float
    dep_bot: float
    dep_wt: float
    no3_n: float
    sol_p: float
    carbon: float
    flo_dist: float
    bf_max: float
    alpha_bf: float
    revap: float
    rchg_dp: float
    spec_yld: float
    hl_no3n: float
    flo_min: float
    revap_min: float


class AquiferAqu(ParsedFile):
    """Contents of an ``aquifer.aqu`` file."""

    rows: tuple[AquiferAquRow, ...]

    def by_name(self, name: str) -> AquiferAquRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_aquifer_aqu(path: Path) -> AquiferAqu:
    """Parse an ``aquifer.aqu`` file into an :class:`AquiferAqu` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[AquiferAquRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return AquiferAqu(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> AquiferAquRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    row_id = parse_int(line.tokens[0], path=path, line_no=ln, field="id")
    name = line.tokens[1]
    init = line.tokens[2]
    float_values = {
        field: parse_float(line.tokens[i + 3], path=path, line_no=ln, field=field)
        for i, field in enumerate(_FLOAT_FIELDS)
    }
    return AquiferAquRow(id=row_id, name=name, init=init, **float_values)
