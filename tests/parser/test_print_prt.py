"""Tests for ``swatplus_ai.parser.inputs.print_prt``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.print_prt import PrintPrt, parse_print_prt

_CROP_YLD_PRT = """\
print.prt: synthetic rev.61.0.1 sample (SWAT+ Editor writer)
nyskip   day_start    yrc_start   day_end   yrc_end   interval
1        0            0           0         0         0
aa_int_cnt
0
csvout    dbout         cdfout
n         n             n
crop_yld  mgtout     hydcon      fdcout
n         y          n           n
objects           daily     monthly        yearly          avann
basin_wb              n           n             n              y
"""

_BOGUS_SOILOUT_PRT = """\
print.prt: synthetic sample with bogus soilout-row header
nyskip   day_start    yrc_start   day_end   yrc_end   interval
1        0            0           0         0         0
aa_int_cnt
0
csvout    dbout         cdfout
n         n             n
foobar    mgtout     hydcon      fdcout
n         y          n           n
objects           daily     monthly        yearly          avann
basin_wb              n           n             n              y
"""

_CROP_YLD_B_PRT = """\
print.prt: synthetic rev.61.0.1 sample with SWAT+ Editor 'b' value
nyskip   day_start    yrc_start   day_end   yrc_end   interval
1        0            0           0         0         0
aa_int_cnt
0
csvout    dbout         cdfout
n         n             n
crop_yld  mgtout     hydcon      fdcout
b         n          n           n
objects           daily     monthly        yearly          avann
basin_wb              n           n             n              y
"""

_CROP_YLD_A_PRT = """\
print.prt: synthetic rev.61.0.1 sample with Fortran-default 'a' value
nyskip   day_start    yrc_start   day_end   yrc_end   interval
1        0            0           0         0         0
aa_int_cnt
0
csvout    dbout         cdfout
n         n             n
crop_yld  mgtout     hydcon      fdcout
a         n          n           n
objects           daily     monthly        yearly          avann
basin_wb              n           n             n              y
"""

_B_IN_MGTOUT_COLUMN_PRT = """\
print.prt: synthetic sample with 'b' in the mgtout column (not allowed)
nyskip   day_start    yrc_start   day_end   yrc_end   interval
1        0            0           0         0         0
aa_int_cnt
0
csvout    dbout         cdfout
n         n             n
crop_yld  mgtout     hydcon      fdcout
n         b          n           n
objects           daily     monthly        yearly          avann
basin_wb              n           n             n              y
"""

_BOGUS_CROP_YLD_VALUE_PRT = """\
print.prt: synthetic sample with bogus crop_yld value
nyskip   day_start    yrc_start   day_end   yrc_end   interval
1        0            0           0         0         0
aa_int_cnt
0
csvout    dbout         cdfout
n         n             n
crop_yld  mgtout     hydcon      fdcout
xx        n          n           n
objects           daily     monthly        yearly          avann
basin_wb              n           n             n              y
"""


def test_parse_minimal(minimal_project: Path) -> None:
    p = parse_print_prt(minimal_project / "print.prt")
    assert isinstance(p, PrintPrt)
    assert p.nyskip == 1
    assert p.day_start == 0
    assert p.interval == 0
    assert p.aa_int_cnt == 0
    assert p.csvout is False
    assert p.dbout is False
    assert p.cdfout is False
    assert p.soilout is False
    assert p.mgtout is True
    assert p.hydcon is False
    assert p.fdcout is False

    assert len(p.objects) == 3
    names = [o.name for o in p.objects]
    assert names == ["basin_wb", "basin_nb", "channel"]
    assert p.objects[0].avann is True
    assert p.objects[1].daily is True
    assert p.objects[2].daily is True
    assert p.objects[2].monthly is True


def test_parse_uru(uru_project: Path) -> None:
    p = parse_print_prt(uru_project / "print.prt")
    assert p.nyskip == 4
    assert p.mgtout is True
    assert len(p.objects) >= 30
    names = {o.name for o in p.objects}
    assert "basin_wb" in names
    assert "channel" in names
    assert "hru_wb" in names


def test_crop_yld_header_accepted(tmp_path: Path) -> None:
    """SWAT+ Editor v3.0+ writes ``crop_yld`` where Toolbox writes ``soilout``."""
    prt = tmp_path / "print.prt"
    prt.write_text(_CROP_YLD_PRT, encoding="utf-8")
    p = parse_print_prt(prt)
    assert p.soilout is False
    assert p.mgtout is True
    assert p.hydcon is False
    assert p.fdcout is False
    assert [o.name for o in p.objects] == ["basin_wb"]


def test_bogus_soilout_header_rejected(tmp_path: Path) -> None:
    """Unknown column name in the soilout section must still fail loud."""
    prt = tmp_path / "print.prt"
    prt.write_text(_BOGUS_SOILOUT_PRT, encoding="utf-8")
    with pytest.raises(ParseError) as excinfo:
        parse_print_prt(prt)
    assert excinfo.value.line_no == 8
    assert "foobar" in str(excinfo.value)


def test_crop_yld_value_b_accepted(tmp_path: Path) -> None:
    """Editor writes ``b`` (both) in column 1 — Fortran-canonical value."""
    prt = tmp_path / "print.prt"
    prt.write_text(_CROP_YLD_B_PRT, encoding="utf-8")
    p = parse_print_prt(prt)
    assert p.soilout is True  # 'b' is truthy
    assert p.mgtout is False
    assert p.hydcon is False
    assert p.fdcout is False


def test_crop_yld_value_a_accepted(tmp_path: Path) -> None:
    """``a`` (average annual) is the Fortran default for column 1."""
    prt = tmp_path / "print.prt"
    prt.write_text(_CROP_YLD_A_PRT, encoding="utf-8")
    p = parse_print_prt(prt)
    assert p.soilout is True  # 'a' is truthy


def test_b_in_non_crop_yld_column_rejected(tmp_path: Path) -> None:
    """Columns 2-4 stay strict y/n; ``b`` elsewhere still raises."""
    prt = tmp_path / "print.prt"
    prt.write_text(_B_IN_MGTOUT_COLUMN_PRT, encoding="utf-8")
    with pytest.raises(ParseError) as excinfo:
        parse_print_prt(prt)
    assert excinfo.value.line_no == 9
    assert "'y' or 'n'" in str(excinfo.value)
    assert "mgtout" in str(excinfo.value)


def test_bogus_crop_yld_value_rejected(tmp_path: Path) -> None:
    """Values outside {a, y, b, n} in the crop_yld column still raise."""
    prt = tmp_path / "print.prt"
    prt.write_text(_BOGUS_CROP_YLD_VALUE_PRT, encoding="utf-8")
    with pytest.raises(ParseError) as excinfo:
        parse_print_prt(prt)
    assert excinfo.value.line_no == 9
    assert "'a', 'y', 'b', 'n'" in str(excinfo.value)
    assert "xx" in str(excinfo.value)
