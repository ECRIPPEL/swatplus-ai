"""Tests for ``swatplus_ai.parser.inputs.codes_bsn``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.codes_bsn import CodesBsn, parse_codes_bsn


def test_parse_minimal(minimal_project: Path) -> None:
    c = parse_codes_bsn(minimal_project / "codes.bsn")
    assert isinstance(c, CodesBsn)
    assert c.pet_file is None
    assert c.wq_file is None
    assert c.pet == 1
    assert c.swift_out == 1
    assert c.wq_cha == 1
    assert c.atmo_dep == "a"
    assert c.i_fpwet == 1
    assert c.gwflow == 0


def test_parse_uru(uru_project: Path) -> None:
    c = parse_codes_bsn(uru_project / "codes.bsn")
    # atmo_dep is always a single-char code in SWAT+ URU-style projects.
    assert len(c.atmo_dep) >= 1


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "codes.bsn"
    p.write_text(
        "codes.bsn: synthetic\n"
        "pet_file wq_file pet event crack swift_out sed_det rte_cha deg_cha "
        "wq_cha nostress cn c_fact carbon lapse uhyd sed_cha tiledrain wtable "
        "soil_p gampt atmo_dep stor_max i_fpwet NOPE\n"
        "null null 1 0 0 1 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 a 0 1 0\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_codes_bsn(p)


def test_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "codes.bsn"
    p.write_text(
        "codes.bsn: synthetic\n"
        "pet_file wq_file pet event crack swift_out sed_det rte_cha deg_cha "
        "wq_cha nostress cn c_fact carbon lapse uhyd sed_cha tiledrain wtable "
        "soil_p gampt atmo_dep stor_max i_fpwet gwflow\n"
        "null null 1 0 0 1 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 a 0 1\n"  # 24, need 25
    )
    with pytest.raises(ParseError, match=r"codes\.bsn value row"):
        parse_codes_bsn(p)


def test_non_integer_switch_raises(tmp_path: Path) -> None:
    p = tmp_path / "codes.bsn"
    p.write_text(
        "codes.bsn: synthetic\n"
        "pet_file wq_file pet event crack swift_out sed_det rte_cha deg_cha "
        "wq_cha nostress cn c_fact carbon lapse uhyd sed_cha tiledrain wtable "
        "soil_p gampt atmo_dep stor_max i_fpwet gwflow\n"
        "null null XXX 0 0 1 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 a 0 1 0\n"
    )
    with pytest.raises(ParseError, match="expected integer for 'pet'"):
        parse_codes_bsn(p)
