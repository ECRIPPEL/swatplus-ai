"""Tests for ``swatplus_ai.parser.inputs.file_cio``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import UnsupportedSwatPlusVersionError
from swatplus_ai.parser.inputs.file_cio import (
    FileCio,
    check_swatplus_version,
    parse_file_cio,
    parse_swatplus_rev,
)


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


class TestSwatplusVersionGate:
    """Behaviour of the ``rev.61+`` floor enforced via :func:`check_swatplus_version`."""

    def _cio(self, tmp_path: Path, title: str) -> FileCio:
        p = tmp_path / "file.cio"
        p.write_text(title + "\nsimulation time.sim print.prt null null null\n")
        return parse_file_cio(p)

    def test_rev_triple_parses(self) -> None:
        assert parse_swatplus_rev("61.0.2") == (61, 0, 2)
        assert parse_swatplus_rev("60.5.4") == (60, 5, 4)
        assert parse_swatplus_rev("61.0.2-dev") == (61, 0, 2)

    def test_rev_triple_rejects_junk(self) -> None:
        assert parse_swatplus_rev(None) is None
        assert parse_swatplus_rev("") is None
        assert parse_swatplus_rev("beta") is None
        assert parse_swatplus_rev("61.0") is None

    def test_rev61_accepted(self, tmp_path: Path) -> None:
        cio = self._cio(
            tmp_path,
            "file.cio: written by SWAT+ editor v3.1.4 on 2026-03-18 for SWAT+ rev.61.0.2",
        )
        check_swatplus_version(cio)  # no raise

    def test_rev60_rejected(self, tmp_path: Path) -> None:
        cio = self._cio(
            tmp_path,
            "file.cio: written by SWAT+ editor v2.1.3 on 2022-11-10 for SWAT+ rev.60.5.4",
        )
        with pytest.raises(UnsupportedSwatPlusVersionError) as exc_info:
            check_swatplus_version(cio)
        msg = str(exc_info.value)
        assert "rev.60.5.4" in msg
        assert "rev.61+" in msg

    def test_unparseable_version_fails_open(self, tmp_path: Path) -> None:
        """An exotic or custom-build version shouldn't be silently blocked —
        if the project has real problems, downstream parsers will surface
        them."""
        cio = self._cio(
            tmp_path,
            "file.cio: custom build for SWAT+ rev.experimental",
        )
        check_swatplus_version(cio)  # no raise
