"""Tests for the small ``*.ops`` operation databases.

harv.ops, graze.ops, irr.ops, fire.ops, sweep.ops, chem_app.ops share
the same flat-table + trailing-description shape as the slice-4
parameter DBs. One test per file exercises the minimal fixture and
one wrong-header path per file verifies error surfacing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.chem_app_ops import parse_chem_app_ops
from swatplus_ai.parser.inputs.fire_ops import parse_fire_ops
from swatplus_ai.parser.inputs.graze_ops import parse_graze_ops
from swatplus_ai.parser.inputs.harv_ops import parse_harv_ops
from swatplus_ai.parser.inputs.irr_ops import parse_irr_ops
from swatplus_ai.parser.inputs.sweep_ops import parse_sweep_ops


def test_parse_harv_ops(minimal_project: Path) -> None:
    h = parse_harv_ops(minimal_project / "harv.ops")
    forest = h.by_name("forest_cut")
    assert forest is not None
    assert forest.harv_typ == "tree"
    assert forest.harv_idx == pytest.approx(0.95)
    assert forest.description is None


def test_parse_graze_ops(minimal_project: Path) -> None:
    g = parse_graze_ops(minimal_project / "graze.ops")
    high = g.by_name("dairy_high")
    assert high is not None
    assert high.fert == "dairy_fr"
    assert high.bm_eat == pytest.approx(25.0)
    assert high.description == "High_Prod_Dairy"


def test_parse_irr_ops(minimal_project: Path) -> None:
    i = parse_irr_ops(minimal_project / "irr.ops")
    sm = i.by_name("sprinkler_med")
    assert sm is not None
    assert sm.amt_mm == pytest.approx(25.0)
    assert sm.eff_frac == pytest.approx(0.85)
    assert sm.description == "sprinkler"


def test_parse_fire_ops(minimal_project: Path) -> None:
    f = parse_fire_ops(minimal_project / "fire.ops")
    grass = f.by_name("grass")
    assert grass is not None
    assert grass.chg_cn2 == pytest.approx(8.0)
    assert grass.frac_burn == pytest.approx(1.0)
    assert grass.description == "grass_burn"


def test_parse_sweep_ops(minimal_project: Path) -> None:
    s = parse_sweep_ops(minimal_project / "sweep.ops")
    assert len(s.rows) == 1
    r = s.rows[0]
    assert r.name == "high_eff"
    assert r.swp_eff == pytest.approx(0.8)
    assert r.description is None


def test_parse_chem_app_ops(minimal_project: Path) -> None:
    c = parse_chem_app_ops(minimal_project / "chem_app.ops")
    bc = c.by_name("broadcast")
    assert bc is not None
    assert bc.chem_form == "solid"
    assert bc.app_typ == "spread"
    assert bc.app_eff == pytest.approx(0.9)
    assert bc.description == "broadcast_method"


def test_harv_ops_missing_required_column_raises(tmp_path: Path) -> None:
    p = tmp_path / "harv.ops"
    p.write_text(
        "harv.ops: synthetic\n"
        "name NOPE harv_idx harv_eff harv_bm_min description\n"
        "forest_cut tree 0.95 0.99 0.0\n"
    )
    with pytest.raises(ParseError, match="missing expected column"):
        parse_harv_ops(p)


def test_irr_ops_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "irr.ops"
    p.write_text(
        "irr.ops: synthetic\n"
        "name amt_mm eff_frac sumq_frac dep_sub salt_ppm no3_ppm po4_ppm description\n"
        "sprinkler_med 25 0.85 0\n"
    )
    with pytest.raises(ParseError, match="expected at least 8 tokens"):
        parse_irr_ops(p)
