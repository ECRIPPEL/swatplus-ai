"""Tests for ``swatplus_ai.parser.inputs.hydrology_hyd``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.hydrology_hyd import HydrologyHyd, parse_hydrology_hyd


def test_parse_minimal(minimal_project: Path) -> None:
    h = parse_hydrology_hyd(minimal_project / "hydrology.hyd")
    assert isinstance(h, HydrologyHyd)
    assert len(h.rows) == 2

    r1 = h.rows[0]
    assert r1.name == "hyd00001"
    assert r1.esco == pytest.approx(0.95)
    assert r1.epco == pytest.approx(0.50)
    assert r1.can_max == pytest.approx(1.0)
    assert r1.perco == pytest.approx(0.05)

    r2 = h.rows[1]
    assert r2.name == "hyd00002"
    assert r2.lat_ttime == pytest.approx(0.5)
    assert r2.perco == pytest.approx(0.5)

    assert h.by_name("hyd00002") is r2
    assert h.by_name("nonexistent") is None


def test_parse_uru(uru_project: Path) -> None:
    h = parse_hydrology_hyd(uru_project / "hydrology.hyd")
    # URU has one hydrology row per HRU; the count must be stable and large.
    assert len(h.rows) > 10_000
    # Every row's name should be unique and start with 'hyd'.
    names = [r.name for r in h.rows]
    assert len(set(names)) == len(names)
    assert all(n.startswith("hyd") for n in names)
    # Spot-check the first row resolves via by_name.
    first = h.rows[0]
    assert h.by_name(first.name) is first


def test_wrong_header_raises(tmp_path: Path) -> None:
    p = tmp_path / "hydrology.hyd"
    p.write_text(
        "hydrology.hyd: synthetic\n"
        "name lat_ttime lat_sed can_max esco epco orgn_enrich orgp_enrich "
        "cn3_swf bio_mix perco lat_orgn lat_orgp pet_co NOPE\n"
        "hyd00001 0 0 1 0.95 0.5 0 0 0.95 0.2 0.05 0 0 1 0.01\n"
    )
    with pytest.raises(ParseError, match="expected header"):
        parse_hydrology_hyd(p)


def test_row_wrong_column_count_raises(tmp_path: Path) -> None:
    p = tmp_path / "hydrology.hyd"
    p.write_text(
        "hydrology.hyd: synthetic\n"
        "name lat_ttime lat_sed can_max esco epco orgn_enrich orgp_enrich "
        "cn3_swf bio_mix perco lat_orgn lat_orgp pet_co latq_co\n"
        "hyd00001 0 0 1 0.95 0.5 0 0 0.95 0.2 0.05 0 0 1\n"  # missing last col
    )
    with pytest.raises(ParseError, match="expected 15 tokens"):
        parse_hydrology_hyd(p)


def test_non_float_value_raises(tmp_path: Path) -> None:
    p = tmp_path / "hydrology.hyd"
    p.write_text(
        "hydrology.hyd: synthetic\n"
        "name lat_ttime lat_sed can_max esco epco orgn_enrich orgp_enrich "
        "cn3_swf bio_mix perco lat_orgn lat_orgp pet_co latq_co\n"
        "hyd00001 0 0 1 NOPE 0.5 0 0 0.95 0.2 0.05 0 0 1 0.01\n"
    )
    with pytest.raises(ParseError, match="esco"):
        parse_hydrology_hyd(p)
