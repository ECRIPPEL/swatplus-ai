"""Parser for ``codes.bsn`` — SWAT+ basin-wide algorithm switches.

Single-row file (like ``time.sim``): title, 25-column header, one value
row. Most columns are integer switches that select a numerical method
or toggle a model component; two are nullable string filenames
(``pet_file``, ``wq_file``) and ``atmo_dep`` is a short code string.

These switches directly affect calibration because changing an
algorithm re-shapes the response of the parameters in ``parameters.bsn``.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser._base import (
    LineReader,
    ParseError,
    expect_tokens,
    parse_int,
    parse_nullable_str,
)
from swatplus_ai.parser.models import ParsedFile

_HEADER: tuple[str, ...] = (
    "pet_file",
    "wq_file",
    "pet",
    "event",
    "crack",
    "swift_out",
    "sed_det",
    "rte_cha",
    "deg_cha",
    "wq_cha",
    "nostress",
    "cn",
    "c_fact",
    "carbon",
    "lapse",
    "uhyd",
    "sed_cha",
    "tiledrain",
    "wtable",
    "soil_p",
    "gampt",
    "atmo_dep",
    "stor_max",
    "i_fpwet",
    "gwflow",
)

_COL_COUNT = len(_HEADER)

_INT_FIELDS: tuple[str, ...] = (
    "pet",
    "event",
    "crack",
    "swift_out",
    "sed_det",
    "rte_cha",
    "deg_cha",
    "wq_cha",
    "nostress",
    "cn",
    "c_fact",
    "carbon",
    "lapse",
    "uhyd",
    "sed_cha",
    "tiledrain",
    "wtable",
    "soil_p",
    "gampt",
    "stor_max",
    "i_fpwet",
    "gwflow",
)


class CodesBsn(ParsedFile):
    """Contents of ``codes.bsn``: one record of algorithm switches."""

    pet_file: str | None
    wq_file: str | None
    pet: int
    event: int
    crack: int
    swift_out: int
    sed_det: int
    rte_cha: int
    deg_cha: int
    wq_cha: int
    nostress: int
    cn: int
    c_fact: int
    carbon: int
    lapse: int
    uhyd: int
    sed_cha: int
    tiledrain: int
    wtable: int
    soil_p: int
    gampt: int
    atmo_dep: str
    stor_max: int
    i_fpwet: int
    gwflow: int


def parse_codes_bsn(path: Path) -> CodesBsn:
    """Parse a ``codes.bsn`` file into a :class:`CodesBsn` model."""
    reader = LineReader(path)
    title = reader.next().text
    expect_tokens(reader.next(), _HEADER, path=path)

    value_line = reader.next()
    if len(value_line.tokens) != _COL_COUNT:
        raise ParseError(
            path,
            value_line.line_no,
            f"expected {_COL_COUNT} tokens in codes.bsn value row, got {len(value_line.tokens)}",
        )

    by_name = dict(zip(_HEADER, value_line.tokens, strict=True))
    ln = value_line.line_no

    int_values = {
        name: parse_int(by_name[name], path=path, line_no=ln, field=name) for name in _INT_FIELDS
    }

    return CodesBsn(
        source_path=path,
        title=title,
        pet_file=parse_nullable_str(by_name["pet_file"]),
        wq_file=parse_nullable_str(by_name["wq_file"]),
        atmo_dep=by_name["atmo_dep"],
        **int_values,
    )
