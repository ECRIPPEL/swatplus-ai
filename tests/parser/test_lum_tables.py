"""Tests for the three ``*.lum`` lookup tables.

cntable.lum, cons_practice.lum and ovn_table.lum are land-use lookup
databases referenced from ``landuse.lum``. One happy-path test per
file and one error-path test verifies header/row validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.cntable_lum import parse_cntable_lum
from swatplus_ai.parser.inputs.cons_practice_lum import parse_cons_practice_lum
from swatplus_ai.parser.inputs.ovn_table_lum import parse_ovn_table_lum


def test_parse_cntable_lum(minimal_project: Path) -> None:
    c = parse_cntable_lum(minimal_project / "cntable.lum")
    assert len(c.rows) == 2
    bare = c.by_name("fal_bare")
    assert bare is not None
    assert bare.cn_a == pytest.approx(77.0)
    assert bare.cn_d == pytest.approx(94.0)
    assert bare.description == "Fallow"
    assert bare.treat == "Bare_soil"
    assert bare.cond_cov == "----"


def test_parse_cons_practice_lum(minimal_project: Path) -> None:
    c = parse_cons_practice_lum(minimal_project / "cons_practice.lum")
    up = c.by_name("up_down_slope")
    assert up is not None
    assert up.usle_p == pytest.approx(1.0)
    assert up.slp_len_max == pytest.approx(121.0)
    assert up.description == "Up_and_down_slope"
    # Second row omits description.
    cross = c.by_name("cross_slope")
    assert cross is not None
    assert cross.description is None


def test_parse_ovn_table_lum(minimal_project: Path) -> None:
    o = parse_ovn_table_lum(minimal_project / "ovn_table.lum")
    fn = o.by_name("fallow_nores")
    assert fn is not None
    assert fn.ovn_mean == pytest.approx(0.01)
    assert fn.ovn_min == pytest.approx(0.008)
    assert fn.ovn_max == pytest.approx(0.012)
    assert fn.description == "Fallow_no_residue"
    ct = o.by_name("convtill_nores")
    assert ct is not None
    assert ct.description is None


def test_cntable_lum_wrong_token_count_raises(tmp_path: Path) -> None:
    # cntable.lum requires exactly 8 tokens per row (strict, not min).
    p = tmp_path / "cntable.lum"
    p.write_text(
        "cntable.lum: synthetic\n"
        "name cn_a cn_b cn_c cn_d description treat cond_cov\n"
        "fal_bare 77 86 91 94 Fallow Bare_soil\n"
    )
    with pytest.raises(ParseError, match="expected 8 tokens"):
        parse_cntable_lum(p)


def test_cons_practice_lum_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "cons_practice.lum"
    p.write_text(
        "cons_practice.lum: synthetic\n"
        "name NOPE slp_len_max description\n"
        "up_down_slope 1.0 121 desc\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_cons_practice_lum(p)


def test_ovn_table_lum_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "ovn_table.lum"
    p.write_text(
        "ovn_table.lum: synthetic\n"
        "name ovn_mean ovn_min ovn_max description\n"
        "fallow_nores 0.01 0.008\n"
    )
    with pytest.raises(ParseError, match="expected at least 4 tokens"):
        parse_ovn_table_lum(p)
