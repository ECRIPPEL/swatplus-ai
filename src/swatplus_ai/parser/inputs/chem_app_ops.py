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
    expect_tokens,
    parse_float,
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
_MIN_TOKENS = 3 + len(_FLOAT_FIELDS)


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
    expect_tokens(reader.next(), _HEADER, path=path)

    rows: list[ChemAppOpsRow] = []
    while not reader.eof():
        rows.append(_parse_row(reader.next(), path=path))
    return ChemAppOps(source_path=path, title=title, rows=tuple(rows))


def _parse_row(line: Line, *, path: Path) -> ChemAppOpsRow:
    if len(line.tokens) < _MIN_TOKENS:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_MIN_TOKENS} tokens "
            f"(name + chem_form + app_typ + {len(_FLOAT_FIELDS)} floats), "
            f"got {len(line.tokens)}",
        )
    name, chem_form, app_typ, *rest = line.tokens
    float_toks = rest[: len(_FLOAT_FIELDS)]
    desc_toks = rest[len(_FLOAT_FIELDS) :]
    values = {
        field: parse_float(tok, path=path, line_no=line.line_no, field=field)
        for field, tok in zip(_FLOAT_FIELDS, float_toks, strict=True)
    }
    description = " ".join(desc_toks) if desc_toks else None
    return ChemAppOpsRow(
        name=name,
        chem_form=chem_form,
        app_typ=app_typ,
        description=description,
        **values,
    )
