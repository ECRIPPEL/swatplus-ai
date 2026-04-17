"""Tests for slice-9 decision-table parsers.

Covers the shared condition/action grid parser backing ``lum.dtl``
(land-use management rules) and ``res_rel.dtl`` (reservoir / wetland
release policies), plus hand-edit safety: the declared count on line 2
is informational only — the parser reads tables until EOF so users can
add or remove tables manually without re-running the SWAT+ editor.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.lum_dtl import parse_lum_dtl
from swatplus_ai.parser.inputs.res_rel_dtl import parse_res_rel_dtl

# --- lum.dtl -------------------------------------------------------------


def test_parse_lum_dtl_minimal(minimal_project: Path) -> None:
    d = parse_lum_dtl(minimal_project / "lum.dtl")
    assert len(d.tables) == 2

    pl = d.by_name("pl_hv_basic")
    assert pl is not None
    assert pl.description == "minimal plant/harvest"
    assert pl.conds == 1
    assert pl.alts == 1
    assert pl.acts == 1
    assert len(pl.conditions) == 1
    assert len(pl.actions) == 1

    cond = pl.conditions[0]
    assert cond.var == "phu_base0"
    assert cond.obj == "hru"
    assert cond.obj_num == 0
    assert cond.lim_var is None  # the 'null' literal parses to None
    assert cond.lim_op == "-"
    assert cond.lim_const == pytest.approx(0.15)
    assert cond.alts == (">",)
    assert cond.comment == "heat units to plant"

    act = pl.actions[0]
    assert act.act_typ == "plant"
    assert act.name == "plant"
    assert act.option == "crop"
    assert act.fp is None
    assert act.outcome == (True,)

    irr = d.by_name("irr_basic")
    assert irr is not None
    assert irr.description is None


def test_parse_lum_dtl_uru(uru_project: Path) -> None:
    d = parse_lum_dtl(uru_project / "lum.dtl")
    # URU lum.dtl ships 40 management decision tables.
    assert len(d.tables) == 40
    summer1 = d.by_name("pl_hv_summer1")
    assert summer1 is not None
    assert summer1.conds == 6
    assert summer1.alts == 5
    assert summer1.acts == 3


def test_parse_lum_dtl_by_name_missing(minimal_project: Path) -> None:
    d = parse_lum_dtl(minimal_project / "lum.dtl")
    assert d.by_name("does_not_exist") is None


# --- res_rel.dtl ---------------------------------------------------------


def test_parse_res_rel_dtl_minimal(minimal_project: Path) -> None:
    d = parse_res_rel_dtl(minimal_project / "res_rel.dtl")
    assert len(d.tables) == 1
    t = d.by_name("flood_simple")
    assert t is not None
    assert t.conds == 1
    assert t.actions[0].act_typ == "release"
    assert t.actions[0].fp == "pvol"


def test_parse_res_rel_dtl_uru(uru_project: Path) -> None:
    d = parse_res_rel_dtl(uru_project / "res_rel.dtl")
    # URU res_rel.dtl ships 3 release policies.
    assert len(d.tables) == 3
    flood = d.by_name("flood_season")
    assert flood is not None
    assert flood.conds == 5
    assert flood.alts == 5
    assert flood.acts == 5


# --- hand-edit safety ----------------------------------------------------


def test_declared_count_is_ignored(tmp_path: Path) -> None:
    """A stale declared count must not prevent parsing the actual tables."""
    p = tmp_path / "lum.dtl"
    # Declared count says 99 but there is only 1 table — must still parse.
    p.write_text(
        "lum.dtl: synthetic\n99\n"
        "name  conds  alts  acts\n"
        "solo   1      1     1\n"
        "var  obj  obj_num  lim_var  lim_op  lim_const  alt1\n"
        "phu_base0  hru  0  null  -  0.15  >\n"
        "act_typ  obj  obj_num  name  option  const  const2  fp  outcome\n"
        "plant  hru  0  plant  crop  0.0  0.0  null  y\n"
    )
    d = parse_lum_dtl(p)
    assert len(d.tables) == 1
    assert d.tables[0].name == "solo"


def test_extra_hand_added_table_is_parsed(tmp_path: Path) -> None:
    """A user-appended third table must be detected beyond the declared 2."""
    p = tmp_path / "lum.dtl"
    body = (
        "lum.dtl: synthetic\n2\n"
        # table 1
        "name  conds  alts  acts\n"
        "t1  1  1  1\n"
        "var  obj  obj_num  lim_var  lim_op  lim_const  alt1\n"
        "phu_base0  hru  0  null  -  0.1  >\n"
        "act_typ  obj  obj_num  name  option  const  const2  fp  outcome\n"
        "plant  hru  0  plant  crop  0.0  0.0  null  y\n"
        # table 2
        "name  conds  alts  acts\n"
        "t2  1  1  1\n"
        "var  obj  obj_num  lim_var  lim_op  lim_const  alt1\n"
        "phu_base0  hru  0  null  -  0.2  >\n"
        "act_typ  obj  obj_num  name  option  const  const2  fp  outcome\n"
        "plant  hru  0  plant  crop  0.0  0.0  null  y\n"
        # table 3 — hand-added after the declared count
        "name  conds  alts  acts\n"
        "t3  1  1  1\n"
        "var  obj  obj_num  lim_var  lim_op  lim_const  alt1\n"
        "phu_base0  hru  0  null  -  0.3  >\n"
        "act_typ  obj  obj_num  name  option  const  const2  fp  outcome\n"
        "plant  hru  0  plant  crop  0.0  0.0  null  y\n"
    )
    p.write_text(body)
    d = parse_lum_dtl(p)
    assert [t.name for t in d.tables] == ["t1", "t2", "t3"]


# --- error paths ---------------------------------------------------------


def test_bad_count_line_raises(tmp_path: Path) -> None:
    p = tmp_path / "lum.dtl"
    p.write_text("lum.dtl: synthetic\ntwo tables\n")
    with pytest.raises(ParseError, match="single-integer table count"):
        parse_lum_dtl(p)


def test_bad_condition_token_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "lum.dtl"
    p.write_text(
        "lum.dtl: synthetic\n1\n"
        "name  conds  alts  acts\n"
        "t1  1  1  1\n"
        "var  obj  obj_num  lim_var  lim_op  lim_const  alt1\n"
        "phu_base0  hru  0  null  -  0.1\n"  # missing alt1 value
    )
    with pytest.raises(ParseError, match="expected 7 tokens for condition row"):
        parse_lum_dtl(p)


def test_bad_action_yn_raises(tmp_path: Path) -> None:
    p = tmp_path / "lum.dtl"
    p.write_text(
        "lum.dtl: synthetic\n1\n"
        "name  conds  alts  acts\n"
        "t1  1  1  1\n"
        "var  obj  obj_num  lim_var  lim_op  lim_const  alt1\n"
        "phu_base0  hru  0  null  -  0.1  >\n"
        "act_typ  obj  obj_num  name  option  const  const2  fp  outcome\n"
        "plant  hru  0  plant  crop  0.0  0.0  null  MAYBE\n"
    )
    with pytest.raises(ParseError, match="expected 'y' or 'n'"):
        parse_lum_dtl(p)
