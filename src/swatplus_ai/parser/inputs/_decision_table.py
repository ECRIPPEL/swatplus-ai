"""Shared parser for SWAT+ decision-table (``*.dtl``) files.

``lum.dtl`` and ``res_rel.dtl`` share the same condition/action grid
idiom. Each file begins with a title and a single-integer declared
count, then contains a series of independent decision tables.

One table looks like::

    name   conds   alts   acts    !<optional description>
    <tbl>   <c>    <a>    <ac>
    var  obj  obj_num  lim_var  lim_op  lim_const  alt1 ... alt<a>
    <c> condition rows, each 6 base tokens + <a> alt symbols
    act_typ  obj  obj_num  name  option  const  const2  fp  outcome
    <ac> action rows, each 8 base tokens + <a> y/n outcome columns

Trailing ``!comments`` on any row are stripped to a descriptive string.
The action sub-header is fixed (nine labels — the ``outcome`` label
stands in for the dynamic alt1..alt<a> y/n block).

**Table count is auto-detected.** Users can hand-edit these files to
add, remove, or reorder tables without updating the declared count on
line 2, so we validate that line is a single integer but iterate until
EOF instead of trusting it.
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
    parse_nullable_str,
    parse_yn,
)

_TABLE_HEADER: tuple[str, ...] = ("name", "conds", "alts", "acts")
_COND_BASE_HEADER: tuple[str, ...] = (
    "var",
    "obj",
    "obj_num",
    "lim_var",
    "lim_op",
    "lim_const",
)
_ACT_HEADER: tuple[str, ...] = (
    "act_typ",
    "obj",
    "obj_num",
    "name",
    "option",
    "const",
    "const2",
    "fp",
    "outcome",
)


class DtlCondition(BaseModel):
    """One condition row inside a decision table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    var: str
    obj: str
    obj_num: int
    lim_var: str | None
    lim_op: str
    lim_const: float
    alts: tuple[str, ...]
    comment: str | None


class DtlAction(BaseModel):
    """One action row inside a decision table."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    act_typ: str
    obj: str
    obj_num: int
    name: str
    option: str | None
    const: float
    const2: float
    fp: str | None
    outcome: tuple[bool, ...]
    comment: str | None


class DecisionTable(BaseModel):
    """One decision table: name, dimensions, conditions and actions."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    conds: int
    alts: int
    acts: int
    description: str | None
    conditions: tuple[DtlCondition, ...]
    actions: tuple[DtlAction, ...]


def parse_decision_tables(path: Path) -> tuple[str, tuple[DecisionTable, ...]]:
    """Parse a ``*.dtl`` file into its title + tuple of decision tables.

    The declared count on line 2 is validated as an integer but not
    used for iteration — users can hand-edit tables in or out without
    updating it, so we read tables until EOF.
    """
    reader = LineReader(path)
    title = reader.next().text
    count_line = reader.next()
    count_tokens, _ = _split_comment(count_line)
    if len(count_tokens) != 1:
        raise ParseError(
            path,
            count_line.line_no,
            f"expected single-integer table count, got {list(count_line.tokens)}",
        )
    parse_int(
        count_tokens[0],
        path=path,
        line_no=count_line.line_no,
        field="declared_table_count",
    )

    tables: list[DecisionTable] = []
    while not reader.eof():
        tables.append(_parse_one_table(reader, path=path))
    return title, tuple(tables)


def _parse_one_table(reader: LineReader, *, path: Path) -> DecisionTable:
    header_line = reader.next()
    header_tokens, description = _split_comment(header_line)
    expect_tokens(
        Line(line_no=header_line.line_no, text=header_line.text, tokens=header_tokens),
        _TABLE_HEADER,
        path=path,
    )

    value_line = reader.next()
    value_tokens, _ = _split_comment(value_line)
    if len(value_tokens) != 4:
        raise ParseError(
            path,
            value_line.line_no,
            f"expected 4 tokens (name conds alts acts), got {list(value_tokens)}",
        )
    ln = value_line.line_no
    name = value_tokens[0]
    conds_n = parse_int(value_tokens[1], path=path, line_no=ln, field="conds")
    alts_n = parse_int(value_tokens[2], path=path, line_no=ln, field="alts")
    acts_n = parse_int(value_tokens[3], path=path, line_no=ln, field="acts")

    cond_header = reader.next()
    cond_header_tokens, _ = _split_comment(cond_header)
    expected_cond_header = (
        *_COND_BASE_HEADER,
        *tuple(f"alt{i}" for i in range(1, alts_n + 1)),
    )
    expect_tokens(
        Line(line_no=cond_header.line_no, text=cond_header.text, tokens=cond_header_tokens),
        expected_cond_header,
        path=path,
    )

    conditions: list[DtlCondition] = []
    for _ in range(conds_n):
        conditions.append(_parse_condition(reader.next(), alts_n=alts_n, path=path))

    act_header = reader.next()
    act_header_tokens, _ = _split_comment(act_header)
    expect_tokens(
        Line(line_no=act_header.line_no, text=act_header.text, tokens=act_header_tokens),
        _ACT_HEADER,
        path=path,
    )

    actions: list[DtlAction] = []
    for _ in range(acts_n):
        actions.append(_parse_action(reader.next(), alts_n=alts_n, path=path))

    return DecisionTable(
        name=name,
        conds=conds_n,
        alts=alts_n,
        acts=acts_n,
        description=description,
        conditions=tuple(conditions),
        actions=tuple(actions),
    )


def _parse_condition(line: Line, *, alts_n: int, path: Path) -> DtlCondition:
    tokens, comment = _split_comment(line)
    expected = len(_COND_BASE_HEADER) + alts_n
    if len(tokens) != expected:
        raise ParseError(
            path,
            line.line_no,
            f"expected {expected} tokens for condition row, got {len(tokens)}",
        )
    ln = line.line_no
    return DtlCondition(
        var=tokens[0],
        obj=tokens[1],
        obj_num=parse_int(tokens[2], path=path, line_no=ln, field="obj_num"),
        lim_var=parse_nullable_str(tokens[3]),
        lim_op=tokens[4],
        lim_const=parse_float(tokens[5], path=path, line_no=ln, field="lim_const"),
        alts=tuple(tokens[6 : 6 + alts_n]),
        comment=comment,
    )


def _parse_action(line: Line, *, alts_n: int, path: Path) -> DtlAction:
    tokens, comment = _split_comment(line)
    base = 8
    expected = base + alts_n
    if len(tokens) != expected:
        raise ParseError(
            path,
            line.line_no,
            f"expected {expected} tokens for action row, got {len(tokens)}",
        )
    ln = line.line_no
    outcomes = tuple(
        parse_yn(tok, path=path, line_no=ln, field=f"outcome{i + 1}")
        for i, tok in enumerate(tokens[base : base + alts_n])
    )
    return DtlAction(
        act_typ=tokens[0],
        obj=tokens[1],
        obj_num=parse_int(tokens[2], path=path, line_no=ln, field="obj_num"),
        name=tokens[3],
        option=parse_nullable_str(tokens[4]),
        const=parse_float(tokens[5], path=path, line_no=ln, field="const"),
        const2=parse_float(tokens[6], path=path, line_no=ln, field="const2"),
        fp=parse_nullable_str(tokens[7]),
        outcome=outcomes,
        comment=comment,
    )


def _split_comment(line: Line) -> tuple[tuple[str, ...], str | None]:
    """Split a line's tokens at the first ``!``-prefixed token.

    Returns the data tokens before the ``!`` and the raw comment text
    (everything after ``!`` on the original line, stripped), or
    ``(line.tokens, None)`` if no comment marker is present.
    """
    for i, tok in enumerate(line.tokens):
        if tok.startswith("!"):
            idx = line.text.find("!")
            comment = line.text[idx + 1 :].strip() or None
            return line.tokens[:i], comment
    return line.tokens, None
