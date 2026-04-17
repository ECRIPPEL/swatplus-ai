"""Tests for ``swatplus_ai.parser.inputs.object_cnt``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.object_cnt import ObjectCnt, parse_object_cnt


def test_parse_minimal(minimal_project: Path) -> None:
    o = parse_object_cnt(minimal_project / "object.cnt")
    assert isinstance(o, ObjectCnt)
    assert o.name == "minimal"
    assert o.ls_area == pytest.approx(123.45)
    assert o.tot_area == pytest.approx(200.00)
    assert o.obj == 6
    assert o.hru == 2
    assert o.cha == 1
    assert o.aqu == 1
    assert o.out == 1
    assert o.wro == 0


def test_parse_uru(uru_project: Path) -> None:
    path = uru_project / "object.cnt"
    if not path.is_file():
        pytest.skip("URU fixture does not yet include object.cnt")
    o = parse_object_cnt(path)
    # URU is a single-HRU test basin but still has at least one of each
    # core object type; totals must be strictly positive.
    assert o.obj > 0
    assert o.hru > 0
    assert o.tot_area > 0


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "object.cnt"
    p.write_text(
        "object.cnt: synthetic\n"
        "name ls_area tot_area obj hru lhru rtu gwfl aqu cha res rec exco dlr "
        "can pmp out lcha aqu2d hrd NOPE\n"
        "minimal 1.0 2.0 6 2 0 1 0 1 1 0 0 0 0 0 0 1 0 0 0 0\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_object_cnt(p)


def test_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "object.cnt"
    p.write_text(
        "object.cnt: synthetic\n"
        "name ls_area tot_area obj hru lhru rtu gwfl aqu cha res rec exco dlr "
        "can pmp out lcha aqu2d hrd wro\n"
        "minimal 1.0 2.0 6 2 0 1 0 1 1 0 0 0 0 0 0 1 0 0 0\n"  # 19, need 20
    )
    with pytest.raises(ParseError, match=r"object\.cnt value row"):
        parse_object_cnt(p)


def test_non_integer_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "object.cnt"
    p.write_text(
        "object.cnt: synthetic\n"
        "name ls_area tot_area obj hru lhru rtu gwfl aqu cha res rec exco dlr "
        "can pmp out lcha aqu2d hrd wro\n"
        "minimal 1.0 2.0 XXX 2 0 1 0 1 1 0 0 0 0 0 0 1 0 0 0 0\n"
    )
    with pytest.raises(ParseError, match="expected integer for 'obj'"):
        parse_object_cnt(p)


def test_non_float_area_raises(tmp_path: Path) -> None:
    p = tmp_path / "object.cnt"
    p.write_text(
        "object.cnt: synthetic\n"
        "name ls_area tot_area obj hru lhru rtu gwfl aqu cha res rec exco dlr "
        "can pmp out lcha aqu2d hrd wro\n"
        "minimal NOPE 2.0 6 2 0 1 0 1 1 0 0 0 0 0 0 1 0 0 0 0\n"
    )
    with pytest.raises(ParseError, match="expected float for 'ls_area'"):
        parse_object_cnt(p)
