"""Parser for ``reservoir.res`` — SWAT+ reservoir wiring table.

One row per named reservoir object declared in ``reservoir.con``. The
row wires the reservoir to its initial conditions (``init``, FK into
``initial.res``), hydrology parameters (``hyd`` → ``hydrology.res``),
release decision table (``rel`` → ``res_rel.dtl``), sediment params
(``sed`` → ``sediment.res``), and nutrient params (``nut`` →
``nutrients.res``). Any FK may be ``null`` for unused slots.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_int,
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_FK_FIELDS: tuple[str, ...] = ("init", "hyd", "rel", "sed", "nut")
_HEADER: tuple[str, ...] = ("id", "name", *_FK_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class ReservoirResRow(BaseModel):
    """FK wiring for one reservoir."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    init: str | None
    hyd: str | None
    rel: str | None
    sed: str | None
    nut: str | None


class ReservoirRes(ParsedFile):
    """Contents of a ``reservoir.res`` file."""

    rows: tuple[ReservoirResRow, ...]

    def by_name(self, name: str) -> ReservoirResRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_reservoir_res(path: Path) -> ReservoirRes:
    """Parse a ``reservoir.res`` file into a :class:`ReservoirRes` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[ReservoirResRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return ReservoirRes(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> ReservoirResRow:
    if len(line.tokens) != _EXPECTED_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected {_EXPECTED_TOKENS} tokens, got {len(line.tokens)}",
        )
    ln = line.line_no
    row_id = parse_int(line.tokens[0], path=path, line_no=ln, field="id")
    name = line.tokens[1]
    fk_values = {
        field: parse_nullable_str(line.tokens[i + 2]) for i, field in enumerate(_FK_FIELDS)
    }
    return ReservoirResRow(id=row_id, name=name, **fk_values)
