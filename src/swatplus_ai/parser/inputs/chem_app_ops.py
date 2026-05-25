"""Parser for ``chem_app.ops`` — SWAT+ chemical-application operation DB.

One row per application method (e.g. ``broadcast``, ``band``),
referenced from ``fertilize`` / ``pest_apply`` scheduled-ops.

Columns: ``name``, ``chem_form`` (string: ``solid`` | ``liquid`` | …),
``app_typ`` (string: ``spread`` | ``band`` | ``inject`` | …), 6 floats
(``app_eff``, ``foliar_eff``, ``inject_dp``, ``surf_frac``,
``drift_pot``, ``aerial_unif``), optional trailing ``description``.
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
    "app_eff",
    "foliar_eff",
    "inject_dp",
    "surf_frac",
    "drift_pot",
    "aerial_unif",
)
_HEADER: tuple[str, ...] = (
    "name",
    "chem_form",
    "app_typ",
    *_FLOAT_FIELDS,
    "description",
)
_FILE = "chem_app.ops"


class ChemAppOpsRow(BaseModel):
    """Parameters for a single chemical-application method."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    chem_form: str
    app_typ: str
    app_eff: float
    foliar_eff: float
    inject_dp: float
    surf_frac: float
    drift_pot: float
    aerial_unif: float
    description: str | None


class ChemAppOps(ParsedFile):
    """Contents of a ``chem_app.ops`` file."""

    rows: tuple[ChemAppOpsRow, ...]

    def by_name(self, name: str) -> ChemAppOpsRow | None:
        for row in self.rows:
            if row.name == name:
                return row
        return None


def parse_chem_app_ops(path: Path) -> ChemAppOps:
    """Parse a ``chem_app.ops`` file into a :class:`ChemAppOps` model."""
    reader = LineReader(path)
    title = reader.next().text
    header_line = reader.next()
    idx_map, unknowns = expect_header_permissive(header_line, _HEADER, path=path)

    rows: list[ChemAppOpsRow] = []
    first_row: Line | None = None
    while not reader.eof():
        line = reader.next()
        if first_row is None:
            first_row = line
        rows.append(_parse_row(line, idx_map=idx_map, path=path))

    record_unknown_columns(unknowns, first_row, file=_FILE)
    return ChemAppOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, idx_map: dict[str, int], path: Path) -> ChemAppOpsRow:
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
    chem_form = tokens[idx_map["chem_form"]]
    app_typ = tokens[idx_map["app_typ"]]
    values = {
        field: parse_float(tokens[idx_map[field]], path=path, line_no=ln, field=field)
        for field in _FLOAT_FIELDS
    }
    desc_toks = tokens[desc_start:]
    description = " ".join(desc_toks) if desc_toks else None
    return ChemAppOpsRow(
        name=name,
        chem_form=chem_form,
        app_typ=app_typ,
        description=description,
        **values,
    )
