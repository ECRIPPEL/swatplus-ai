"""Tests for the routing-unit / landscape-unit topology files.

ls_unit.def + ls_unit.ele pair, rout_unit.def + rout_unit.ele + .rtu
triple, and aqu_catunit.ele all describe element membership and
wiring for the SWAT+ spatial graph.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.aqu_catunit_ele import parse_aqu_catunit_ele
from swatplus_ai.parser.inputs.ls_unit_def import parse_ls_unit_def
from swatplus_ai.parser.inputs.ls_unit_ele import parse_ls_unit_ele
from swatplus_ai.parser.inputs.rout_unit_def import parse_rout_unit_def
from swatplus_ai.parser.inputs.rout_unit_ele import parse_rout_unit_ele
from swatplus_ai.parser.inputs.rout_unit_rtu import parse_rout_unit_rtu


def test_parse_ls_unit_def(minimal_project: Path) -> None:
    d = parse_ls_unit_def(minimal_project / "ls_unit.def")
    assert d.row_count == 1
    assert len(d.rows) == 1
    r = d.by_name("rtu001")
    assert r is not None
    assert r.elem_tot == 2
    # Range sentinel: 1..-2 means HRUs 1..2.
    assert r.elements == (1, -2)


def test_parse_ls_unit_ele(minimal_project: Path) -> None:
    e = parse_ls_unit_ele(minimal_project / "ls_unit.ele")
    assert len(e.rows) == 2
    r = e.by_name("hru00001")
    assert r is not None
    assert r.obj_typ == "hru"
    assert r.obj_typ_no == 1
    assert r.bsn_frac == pytest.approx(0.5)
    assert r.sub_frac == pytest.approx(1.0)


def test_parse_rout_unit_def(minimal_project: Path) -> None:
    d = parse_rout_unit_def(minimal_project / "rout_unit.def")
    r = d.by_name("rtu001")
    assert r is not None
    assert r.elem_tot == 2
    assert r.elements == (1, -2)


def test_parse_rout_unit_ele(minimal_project: Path) -> None:
    e = parse_rout_unit_ele(minimal_project / "rout_unit.ele")
    assert len(e.rows) == 2
    r = e.by_name("hru00001")
    assert r is not None
    assert r.obj_typ == "hru"
    assert r.obj_id == 1
    assert r.frac == pytest.approx(0.5)
    assert r.dlr == 0


def test_parse_rout_unit_rtu(minimal_project: Path) -> None:
    ru = parse_rout_unit_rtu(minimal_project / "rout_unit.rtu")
    r = ru.by_name("rtu001")
    assert r is not None
    assert r.define == "rtu001"
    assert r.dlr is None
    assert r.topo == "toportu001"
    assert r.field == "fld001"


def test_parse_aqu_catunit_ele(minimal_project: Path) -> None:
    a = parse_aqu_catunit_ele(minimal_project / "aqu_catunit.ele")
    r = a.by_name("aqu001")
    assert r is not None
    assert r.obj_typ == "aqu"
    assert r.bsn_frac == pytest.approx(1.0)


def test_parse_ls_unit_def_uru(uru_project: Path) -> None:
    d = parse_ls_unit_def(uru_project / "ls_unit.def")
    assert d.row_count == len(d.rows)
    assert d.row_count > 100


def test_parse_rout_unit_rtu_uru_null_dlr(uru_project: Path) -> None:
    ru = parse_rout_unit_rtu(uru_project / "rout_unit.rtu")
    # URU writes 'null' for every dlr in rout_unit.rtu.
    assert any(r.dlr is None for r in ru.rows)


def test_ls_unit_def_count_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "ls_unit.def"
    p.write_text("ls_unit.def: synthetic\n5\nid name area elem_tot elements\n1 rtu001 100.0 1 7\n")
    with pytest.raises(ParseError, match="declared row count 5 does not match"):
        parse_ls_unit_def(p)


def test_rout_unit_def_elem_tot_mismatch_raises(tmp_path: Path) -> None:
    p = tmp_path / "rout_unit.def"
    p.write_text("rout_unit.def: synthetic\nid name elem_tot elements\n1 rtu001 3 1 -2\n")
    with pytest.raises(ParseError, match="expected 3 element tokens"):
        parse_rout_unit_def(p)


def test_rout_unit_ele_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "rout_unit.ele"
    p.write_text("rout_unit.ele: synthetic\nid name NOPE obj_id frac dlr\n1 hru00001 hru 1 0.5 0\n")
    with pytest.raises(ParseError, match="expected header"):
        parse_rout_unit_ele(p)


def test_ls_unit_ele_wrong_token_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "ls_unit.ele"
    p.write_text(
        "ls_unit.ele: synthetic\n"
        "id name obj_typ obj_typ_no bsn_frac sub_frac reg_frac\n"
        "1 hru00001 hru 1 0.5 1.0\n"
    )
    with pytest.raises(ParseError, match="expected 7 tokens"):
        parse_ls_unit_ele(p)
