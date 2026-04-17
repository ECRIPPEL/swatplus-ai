"""Shared parser for ``initial.aqu`` / ``initial.cha`` / ``initial.res``.

All three files share the exact same shape: one row per named
initial-condition set with the columns ``name org_min pest path hmet
salt description``. ``org_min`` is a short label (e.g. ``no_init``)
or a reference into ``om_water.ini``; the remaining four FK columns
are nullable (literal ``null`` when unused). A single parser function
handles all three, with the concrete file keyed in by
:class:`InitialAny.source_path`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from swatplus_ai.parser._base import (
    Line,
    LineReader,
    ParseError,
    expect_tokens,
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_FK_FIELDS: tuple[str, ...] = ("pest", "path", "hmet", "salt")
_HEADER: tuple[str, ...] = ("name", "org_min", *_FK_FIELDS, "description")
_MIN_TOKENS = 6  # name org_min + 4 FKs; description optional.


class InitialAnyRow(BaseModel):
    """One initial-condition set shared across aquifer / channel / reservoir."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    org_min: str
    pest: str | None
    path: str | None
    hmet: str | None
    salt: str | None
    description: str | None


class InitialAny(ParsedFile):
    """Contents of an ``initial.{aqu,cha,res}`` file."""

    rows: tuple[InitialAnyRow, ...]

    def by_name(self, name: str) -> InitialAnyRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_initial_any(path: Path) -> InitialAny:
    """Parse any ``initial.{aqu,cha,res}`` file into an :class:`InitialAny`."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[InitialAnyRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return InitialAny(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> InitialAnyRow:
    tokens = line.tokens
    if len(tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens (name org_min + 4 FKs), got {len(tokens)}",
        )
    name = tokens[0]
    org_min = tokens[1]
    fk_values = {field: parse_nullable_str(tokens[i + 2]) for i, field in enumerate(_FK_FIELDS)}
    desc_toks = tokens[_MIN_TOKENS:]
    description = parse_nullable_str(" ".join(desc_toks)) if desc_toks else None
    return InitialAnyRow(name=name, org_min=org_min, description=description, **fk_values)
