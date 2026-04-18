"""Tests for ``swatplus_ai.parser.topology.TopologyAccessor``."""

from __future__ import annotations

import shutil
from pathlib import Path

from swatplus_ai.parser.topology import TopologyAccessor
from swatplus_ai.parser.txtinout import TxtInOutProject


def test_outfall_channels_on_minimal(minimal_project: Path) -> None:
    p = TxtInOutProject.read(minimal_project)
    accessor = p.topology
    assert isinstance(accessor, TopologyAccessor)
    outfalls = accessor.outfall_channels()
    # Every returned name must appear in chandeg.con with out_tot == 0.
    assert p.chandeg_con is not None
    expected = tuple(row.name for row in p.chandeg_con.rows if row.out_tot == 0)
    assert outfalls == expected


def test_outfall_channels_on_uru(uru_project: Path) -> None:
    # URU's basin drains to a single outfall channel, cha033.
    p = TxtInOutProject.read(uru_project)
    assert p.topology.outfall_channels() == ("cha033",)


def test_outfall_channels_absent_chandeg_is_empty(tmp_path: Path, minimal_project: Path) -> None:
    staging = tmp_path / "staging"
    shutil.copytree(minimal_project, staging)
    (staging / "chandeg.con").unlink()
    p = TxtInOutProject.read(staging)
    assert p.chandeg_con is None
    assert p.topology.outfall_channels() == ()
