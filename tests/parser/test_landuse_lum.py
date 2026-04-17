"""Tests for ``swatplus_ai.parser.inputs.landuse_lum``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.landuse_lum import LanduseLum, parse_landuse_lum


def test_parse_minimal(minimal_project: Path) -> None:
    lum = parse_landuse_lum(minimal_project / "landuse.lum")
    assert isinstance(lum, LanduseLum)
    assert len(lum.rows) == 2

    frse = lum.rows[0]
    assert frse.name == "frse_lum"
    assert frse.cal_group is None
    assert frse.plnt_com == "frse_comm"
    assert frse.mgt is None
    assert frse.cn2 == "wood_f"
    assert frse.cons_prac == "up_down_slope"
    assert frse.ov_mann == "forest_heavy"
    assert frse.bmp is None

    corn = lum.rows[1]
    assert corn.name == "corn_lum"
    assert corn.mgt == "corn_rot"
    assert corn.ov_mann == "convtill_res"

    assert lum.by_name("corn_lum") is corn
    assert lum.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    lum = parse_landuse_lum(uru_project / "landuse.lum")
    # URU has dozens of land-use classes; count must be stable across runs.
    assert len(lum.rows) > 10
    # Every row's name must be unique and end with "_lum".
    names = [r.name for r in lum.rows]
    assert len(set(names)) == len(names)
    assert all(n.endswith("_lum") for n in names)

    # Common URU landuses referenced by hru-data.hru should resolve.
    for expected in ("corn_lum", "frse_lum", "alfa_lum"):
        assert lum.by_name(expected) is not None, f"missing {expected}"


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "landuse.lum"
    p.write_text(
        "landuse.lum: synthetic\n"
        "name cal_group plnt_com mgt cn2 cons_prac urban urb_ro ov_mann "
        "tile sep vfs grww NOPE\n"
        "x null null null null null null null null null null null null null\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_landuse_lum(p)


def test_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "landuse.lum"
    p.write_text(
        "landuse.lum: synthetic\n"
        "name cal_group plnt_com mgt cn2 cons_prac urban urb_ro ov_mann "
        "tile sep vfs grww bmp\n"
        "x null null null null null null null null null null null null\n"  # 13, need 14
    )
    with pytest.raises(ParseError, match="expected 14 tokens"):
        parse_landuse_lum(p)
