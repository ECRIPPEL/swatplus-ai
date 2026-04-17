"""Tests for ``swatplus_ai.parser.inputs.management_sch``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.management_sch import ManagementSch, parse_management_sch


def test_parse_minimal(minimal_project: Path) -> None:
    m = parse_management_sch(minimal_project / "management.sch")
    assert isinstance(m, ManagementSch)
    assert len(m.schedules) == 2

    corn = m.schedules[0]
    assert corn.name == "corn_rot"
    assert corn.numb_ops == 0
    assert corn.numb_auto == 1
    assert len(corn.ops) == 0
    assert len(corn.autos) == 1
    assert corn.autos[0].op_typ == "pl_hv_summer1"
    assert corn.autos[0].op_data1 == "corn"

    soyb = m.schedules[1]
    assert soyb.name == "soyb_rot"
    assert soyb.numb_ops == 3
    assert soyb.numb_auto == 0
    assert [op.op_typ for op in soyb.ops] == ["plnt", "hvkl", "till"]
    plnt = soyb.ops[0]
    assert plnt.mon == 3
    assert plnt.day == 20
    assert plnt.hu_sch == pytest.approx(0.0)
    assert plnt.op_data1 == "soyb"
    assert plnt.op_data2 is None  # "null" → None
    assert plnt.op_data3 == pytest.approx(0.0)

    hvkl = soyb.ops[1]
    assert hvkl.op_data2 == "grain"

    assert m.by_name("soyb_rot") is soyb
    assert m.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    m = parse_management_sch(uru_project / "management.sch")
    assert len(m.schedules) > 10
    # Every schedule's op/auto lists must match the declared counts.
    for s in m.schedules:
        assert len(s.ops) == s.numb_ops
        assert len(s.autos) == s.numb_auto
    # A known URU schedule referenced by landuse.lum.mgt should resolve.
    assert m.by_name("corn_rot") is not None
    assert m.by_name("soyb_rot") is not None


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "management.sch"
    p.write_text(
        "management.sch: synthetic\n"
        "name numb_ops numb_auto op_typ mon day hu_sch op_data1 op_data2 NOPE\n"
        "s1 0 1\n"
        "pl_hv_summer1 corn\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_management_sch(p)


def test_schedule_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "management.sch"
    p.write_text(
        "management.sch: synthetic\n"
        "name numb_ops numb_auto op_typ mon day hu_sch op_data1 op_data2 op_data3\n"
        "s1 0\n"  # missing numb_auto
        "pl_hv_summer1 corn\n"
    )
    with pytest.raises(ParseError, match="schedule row"):
        parse_management_sch(p)


def test_scheduled_op_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "management.sch"
    p.write_text(
        "management.sch: synthetic\n"
        "name numb_ops numb_auto op_typ mon day hu_sch op_data1 op_data2 op_data3\n"
        "s1 1 0\n"
        "plnt 3 20 0 soyb null\n"  # 6 tokens, need 7
    )
    with pytest.raises(ParseError, match="scheduled-op row"):
        parse_management_sch(p)


def test_auto_op_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "management.sch"
    p.write_text(
        "management.sch: synthetic\n"
        "name numb_ops numb_auto op_typ mon day hu_sch op_data1 op_data2 op_data3\n"
        "s1 0 1\n"
        "pl_hv_summer1\n"  # only 1 token, need 2
    )
    with pytest.raises(ParseError, match="auto-op row"):
        parse_management_sch(p)


def test_numb_ops_exceeds_available_rows_raises(tmp_path: Path) -> None:
    p = tmp_path / "management.sch"
    p.write_text(
        "management.sch: synthetic\n"
        "name numb_ops numb_auto op_typ mon day hu_sch op_data1 op_data2 op_data3\n"
        "s1 3 0\n"
        "plnt 3 20 0 soyb null 0\n"
        # only 1 op provided but numb_ops claims 3
    )
    with pytest.raises(ParseError, match="numb_ops=3"):
        parse_management_sch(p)
