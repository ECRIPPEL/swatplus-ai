"""Tests for the five ``*.con`` spatial-object connectivity files.

hru.con has no trailing connections; the other four
(aquifer/chandeg/reservoir/rout_unit) all share the same
base-13 + (out_tot x 4) row shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.aquifer_con import parse_aquifer_con
from swatplus_ai.parser.inputs.chandeg_con import parse_chandeg_con
from swatplus_ai.parser.inputs.hru_con import parse_hru_con
from swatplus_ai.parser.inputs.reservoir_con import parse_reservoir_con
from swatplus_ai.parser.inputs.rout_unit_con import parse_rout_unit_con


def test_parse_hru_con(minimal_project: Path) -> None:
    h = parse_hru_con(minimal_project / "hru.con")
    assert len(h.rows) == 2
    r = h.by_name("hru00001")
    assert r is not None
    assert r.gis_id == 1
    assert r.lat == pytest.approx(-26.49376)
    assert r.elev == pytest.approx(696.06188)
    assert r.wst == "sta001"
    assert r.out_tot == 0


def test_parse_aquifer_con(minimal_project: Path) -> None:
    a = parse_aquifer_con(minimal_project / "aquifer.con")
    r = a.by_name("aqu001")
    assert r is not None
    assert r.aqu == 1
    assert r.out_tot == 1
    assert len(r.connections) == 1
    c = r.connections[0]
    assert c.obj_typ == "sdc"
    assert c.obj_id == 1
    assert c.hyd_typ == "tot"
    assert c.frac == pytest.approx(1.0)


def test_parse_chandeg_con(minimal_project: Path) -> None:
    c = parse_chandeg_con(minimal_project / "chandeg.con")
    r = c.by_name("cha001")
    assert r is not None
    assert r.lcha == 1
    assert len(r.connections) == 1


def test_parse_reservoir_con(minimal_project: Path) -> None:
    r = parse_reservoir_con(minimal_project / "reservoir.con")
    row = r.by_name("res001")
    assert row is not None
    assert row.res == 1
    assert len(row.connections) == 1


def test_parse_rout_unit_con(minimal_project: Path) -> None:
    ru = parse_rout_unit_con(minimal_project / "rout_unit.con")
    r = ru.by_name("rtu001")
    assert r is not None
    assert r.rtu == 1
    assert r.out_tot == 2
    assert len(r.connections) == 2
    assert {c.obj_typ for c in r.connections} == {"sdc", "aqu"}


def test_parse_hru_con_uru(uru_project: Path) -> None:
    h = parse_hru_con(uru_project / "hru.con")
    assert len(h.rows) > 1000  # URU has ~12k HRUs
    assert all(row.out_tot == 0 for row in h.rows)


def test_parse_rout_unit_con_uru_variable_connections(uru_project: Path) -> None:
    ru = parse_rout_unit_con(uru_project / "rout_unit.con")
    # URU rout_unit.con has rows with out_tot ranging 2..4.
    counts = {row.out_tot for row in ru.rows}
    assert counts == {2, 4}
    for row in ru.rows:
        assert len(row.connections) == row.out_tot


def test_aquifer_con_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "aquifer.con"
    p.write_text(
        "aquifer.con: synthetic\n"
        "id name gis_id area lat lon elev NOPE wst cst ovfl rule out_tot obj_typ obj_id hyd_typ frac\n"
        "1 aqu001 1 1 0 0 0 1 sta 0 0 0 1 sdc 1 tot 1.0\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_aquifer_con(p)


def test_aquifer_con_mismatched_connections_raises(tmp_path: Path) -> None:
    # out_tot=2 but only one trailing 4-tuple supplied.
    p = tmp_path / "aquifer.con"
    p.write_text(
        "aquifer.con: synthetic\n"
        "id name gis_id area lat lon elev aqu wst cst ovfl rule out_tot obj_typ obj_id hyd_typ frac\n"
        "1 aqu001 1 1 0 0 0 1 sta 0 0 0 2 sdc 1 tot 1.0\n"
    )
    with pytest.raises(ParseError, match=r"expected 8 trailing connection tokens"):
        parse_aquifer_con(p)


def test_hru_con_wrong_token_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "hru.con"
    p.write_text(
        "hru.con: synthetic\n"
        "id name gis_id area lat lon elev hru wst cst ovfl rule out_tot\n"
        "1 hru00001 1 100 -26 -52 700 1 sta001 0 0 0\n"
    )
    with pytest.raises(ParseError, match="expected 13 tokens"):
        parse_hru_con(p)
