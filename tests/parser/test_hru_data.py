"""Tests for ``swatplus_ai.parser.inputs.hru_data``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.hru_data import HruData, parse_hru_data


def test_parse_minimal(minimal_project: Path) -> None:
    h = parse_hru_data(minimal_project / "hru-data.hru")
    assert isinstance(h, HruData)
    assert len(h.rows) == 2

    r1 = h.rows[0]
    assert r1.id == 1
    assert r1.name == "hru00001"
    assert r1.topo == "topohru00001"
    assert r1.hydro == "hyd00001"
    assert r1.soil == "soil1"
    assert r1.lu_mgt == "frse_lum"
    assert r1.soil_plant_init == "soilplant1"
    assert r1.surf_stor is None
    assert r1.snow == "snow001"
    assert r1.field is None

    r2 = h.rows[1]
    assert r2.lu_mgt == "corn_lum"

    assert h.by_id(1) is r1
    assert h.by_id(2) is r2
    assert h.by_id(999) is None
    assert h.by_name("hru00002") is r2
    assert h.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    h = parse_hru_data(uru_project / "hru-data.hru")
    assert len(h.rows) > 10_000
    ids = [r.id for r in h.rows]
    assert ids == sorted(ids), "HRU ids should be monotonically increasing"
    assert len(set(ids)) == len(ids), "HRU ids must be unique"

    # Every hydro reference should look like hydNNNNN (matches hydrology.hyd).
    sample = h.rows[0]
    assert sample.hydro is not None and sample.hydro.startswith("hyd")

    # URU's surf_stor and field are typically null for most/all HRUs.
    assert h.rows[0].surf_stor is None


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "hru-data.hru"
    p.write_text(
        "hru-data.hru: synthetic\n"
        "id name topo hydro soil lu_mgt soil_plant_init surf_stor snow NOPE\n"
        "1 hru1 t1 h1 s1 l1 spi1 null snow1 null\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_hru_data(p)


def test_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "hru-data.hru"
    p.write_text(
        "hru-data.hru: synthetic\n"
        "id name topo hydro soil lu_mgt soil_plant_init surf_stor snow field\n"
        "1 hru1 t1 h1 s1 l1 spi1 null snow1\n"  # missing last col
    )
    with pytest.raises(ParseError, match="expected 10 tokens"):
        parse_hru_data(p)


def test_non_integer_id_raises(tmp_path: Path) -> None:
    p = tmp_path / "hru-data.hru"
    p.write_text(
        "hru-data.hru: synthetic\n"
        "id name topo hydro soil lu_mgt soil_plant_init surf_stor snow field\n"
        "NOPE hru1 t1 h1 s1 l1 spi1 null snow1 null\n"
    )
    with pytest.raises(ParseError, match="id"):
        parse_hru_data(p)
