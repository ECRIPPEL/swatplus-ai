"""Tests for ``swatplus_ai.parser.inputs.file_cio``."""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser.inputs.file_cio import FileCio, parse_file_cio


def test_parse_minimal(minimal_project: Path) -> None:
    f = parse_file_cio(minimal_project / "file.cio")
    assert isinstance(f, FileCio)
    assert f.swatplus_version == "61.0.2"
    assert f.editor_version == "3.1.4"

    simulation = f.section("simulation")
    assert simulation is not None
    assert simulation.files == ("time.sim", "print.prt", None, "object.cnt", None)

    basin = f.section("basin")
    assert basin is not None
    assert basin.files == ("codes.bsn", "parameters.bsn")

    hru = f.section("hru")
    assert hru is not None
    assert hru.files == ("hru-data.hru", None)

    assert f.section("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    f = parse_file_cio(uru_project / "file.cio")
    assert f.swatplus_version == "61.0.2"
    assert f.editor_version == "3.1.4"

    for section_name in ("simulation", "basin", "climate", "hru", "soils"):
        assert f.section(section_name) is not None, f"missing section {section_name}"

    simulation = f.section("simulation")
    assert simulation is not None
    assert simulation.files[0] == "time.sim"
    assert simulation.files[1] == "print.prt"
