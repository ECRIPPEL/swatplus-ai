"""Tests for ``swatplus_ai.parser.outputs.OutputsNamespace``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser.outputs import OutputsNamespace


def test_read_minimal(minimal_project: Path) -> None:
    ns = OutputsNamespace.read(minimal_project)
    assert ns.folder == minimal_project
    assert ns.basin_wb_aa is not None
    assert ns.basin_pw_aa is not None
    assert ns.basin_ls_aa is not None
    assert ns.basin_nb_aa is not None
    assert ns.hru_wb_aa is not None
    assert ns.hru_pw_aa is not None
    assert ns.hru_ls_aa is not None
    assert ns.hru_nb_aa is not None
    assert ns.channel_sd_aa is not None
    assert ns.channel_sdmorph_aa is not None
    assert ns.aquifer_aa is not None
    assert ns.reservoir_aa is not None
    assert ns.wetland_aa is not None


def test_read_empty_folder_tolerant(tmp_path: Path) -> None:
    # No output files present — every field should be None, no exception.
    ns = OutputsNamespace.read(tmp_path)
    assert ns.folder == tmp_path
    assert ns.basin_wb_aa is None
    assert ns.hru_wb_aa is None
    assert ns.channel_sd_aa is None
    assert ns.aquifer_aa is None
    assert ns.reservoir_aa is None
    assert ns.wetland_aa is None


def test_read_missing_folder_raises(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(NotADirectoryError, match="Outputs folder not found"):
        OutputsNamespace.read(missing)
