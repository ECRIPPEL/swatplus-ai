"""Parser for ``fire.ops`` — SWAT+ fire / burn-operation parameter DB.

One row per fire type (e.g. ``grass``, ``tree_intense``), referenced
from ``burn`` scheduled-ops.

Columns: ``name``, 2 floats (``chg_cn2``, ``frac_burn``), optional
trailing ``description``.
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

_FLOAT_FIELDS: tuple[str, ...] = ("chg_cn2", "frac_burn")
_HEADER: tuple[str, ...] = ("name", *_FLOAT_FIELDS, "description")
_MIN_TOKENS = 1 + len(_FLOAT_FIELDS)


class FireOpsRow(BaseModel):
    """Parameters for a single fire operation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    chg_cn2: float
    frac_burn: float
    description: str | None


class FireOps(ParsedFile):
    """Contents of a ``fire.ops`` file."""

    rows: tuple[FireOpsRow, ...]

    def by_name(self, name: str) -> FireOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_fire_ops(path: Path) -> FireOps:
    """Parse a ``fire.ops`` file into a :class:`FireOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[FireOpsRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return FireOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> FireOpsRow:
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
    return FireOpsRow(name=name, description=description, **values)
