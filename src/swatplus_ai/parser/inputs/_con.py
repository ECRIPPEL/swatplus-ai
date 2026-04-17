"""Shared row-parsing helper for SWAT+ ``*.con`` spatial-object files.

``aquifer.con``, ``chandeg.con``, ``reservoir.con`` and ``rout_unit.con``
share the same line shape: 13 base fields followed by ``out_tot`` trailing
``(obj_typ, obj_id, hyd_typ, frac)`` 4-tuples. Only the 8th base-header
name differs (``aqu`` / ``lcha`` / ``res`` / ``rtu`` — a self-index into
the corresponding object-definition file). This module centralises both
the header template and row-parsing so each per-file parser becomes a
thin wrapper.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser._base import (
    Line,
    ParseError,
    parse_float,
    parse_int,
)
from swatplus_ai.parser.models import ConConnection

_BASE_FIELDS_BEFORE_TYPE: tuple[str, ...] = (
    "id",
    "name",
    "gis_id",
    "area",
    "lat",
    "lon",
    "elev",
)
_BASE_FIELDS_AFTER_TYPE: tuple[str, ...] = (
    "wst",
    "cst",
    "ovfl",
    "rule",
    "out_tot",
)
_CONNECTION_FIELDS: tuple[str, ...] = ("obj_typ", "obj_id", "hyd_typ", "frac")
_BASE_TOKEN_COUNT = len(_BASE_FIELDS_BEFORE_TYPE) + 1 + len(_BASE_FIELDS_AFTER_TYPE)


def con_header(type_col: str) -> tuple[str, ...]:
    """Header columns for a connected ``*.con`` file with ``type_col`` at position 8."""
    return (
        *_BASE_FIELDS_BEFORE_TYPE,
        type_col,
        *_BASE_FIELDS_AFTER_TYPE,
        *_CONNECTION_FIELDS,
    )


def parse_con_row(line: Line, *, path: Path) -> tuple[dict[str, object], tuple[ConConnection, ...]]:
    """Parse one ``*.con`` data row into (base-fields dict, connections tuple).

    The base dict keys match the header order, with the 8th column keyed as
    ``"type_col"`` so callers can rename it to the file-specific field name
    when constructing the row model.
    """
    tokens = line.tokens
    if len(tokens) < _BASE_TOKEN_COUNT:
        raise ParseError(
            path,
            line.line_no,
            f"expected at least {_BASE_TOKEN_COUNT} tokens, got {len(tokens)}",
        )
    ln = line.line_no
    base: dict[str, object] = {
        "id": parse_int(tokens[0], path=path, line_no=ln, field="id"),
        "name": tokens[1],
        "gis_id": parse_int(tokens[2], path=path, line_no=ln, field="gis_id"),
        "area": parse_float(tokens[3], path=path, line_no=ln, field="area"),
        "lat": parse_float(tokens[4], path=path, line_no=ln, field="lat"),
        "lon": parse_float(tokens[5], path=path, line_no=ln, field="lon"),
        "elev": parse_float(tokens[6], path=path, line_no=ln, field="elev"),
        "type_col": parse_int(tokens[7], path=path, line_no=ln, field="type_col"),
        "wst": tokens[8],
        "cst": parse_int(tokens[9], path=path, line_no=ln, field="cst"),
        "ovfl": parse_int(tokens[10], path=path, line_no=ln, field="ovfl"),
        "rule": parse_int(tokens[11], path=path, line_no=ln, field="rule"),
        "out_tot": parse_int(tokens[12], path=path, line_no=ln, field="out_tot"),
    }
    out_tot = base["out_tot"]
    assert isinstance(out_tot, int)
    expected_trail = out_tot * len(_CONNECTION_FIELDS)
    trail = tokens[_BASE_TOKEN_COUNT:]
    if len(trail) != expected_trail:
        raise ParseError(
            path,
            ln,
            f"expected {expected_trail} trailing connection tokens "
            f"({out_tot} x 4), got {len(trail)}",
        )
    connections = tuple(
        ConConnection(
            obj_typ=trail[i],
            obj_id=parse_int(trail[i + 1], path=path, line_no=ln, field="obj_id"),
            hyd_typ=trail[i + 2],
            frac=parse_float(trail[i + 3], path=path, line_no=ln, field="frac"),
        )
        for i in range(0, expected_trail, 4)
    )
    return base, connections
