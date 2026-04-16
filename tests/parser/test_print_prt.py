"""Tests for ``swatplus_ai.parser.inputs.print_prt``."""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser.inputs.print_prt import PrintPrt, parse_print_prt


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
