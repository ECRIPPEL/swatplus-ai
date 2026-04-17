"""Parser for ``channel-lte.cha`` — SWAT+ LTE channel wiring table.

One row per named channel object declared in ``chandeg.con``. The row
is a pure FK wiring table pointing at the channel's initial conditions,
hydrology/sediment parameters, sediment-routing parameters (often
``null``), and nutrient parameters.
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

_FK_FIELDS: tuple[str, ...] = ("cha_ini", "cha_hyd", "cha_sed", "cha_nut")
_HEADER: tuple[str, ...] = ("id", "name", *_FK_FIELDS)
_EXPECTED_TOKENS = len(_HEADER)


class ChannelLteChaRow(BaseModel):
    """FK wiring for one LTE channel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: int
    name: str
    cha_ini: str | None
    cha_hyd: str | None
    cha_sed: str | None
    cha_nut: str | None


class ChannelLteCha(ParsedFile):
    """Contents of a ``channel-lte.cha`` file."""

    rows: tuple[ChannelLteChaRow, ...]

    def by_name(self, name: str) -> ChannelLteChaRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_channel_lte_cha(path: Path) -> ChannelLteCha:
    """Parse a ``channel-lte.cha`` file into a :class:`ChannelLteCha` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[ChannelLteChaRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return ChannelLteCha(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> ChannelLteChaRow:
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
    return ChannelLteChaRow(id=row_id, name=name, **fk_values)
