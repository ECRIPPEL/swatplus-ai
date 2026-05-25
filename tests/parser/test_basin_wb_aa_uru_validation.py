"""URU validation fixture for the trailing-scenario stripper (slice 7.3j).

Reproduces the canonical SWAT+ Rev 2026.61.0.2 ``basin_wb_aa.txt``
shape observed in URU-derived dogfood projects: a 51-column header
(49 core + ``plant_cov`` + ``mgt_ops``) followed by data rows of 54
tokens each (51 declared + 3 trailing scenario tokens emitted by the
Fortran driver). Post-strip, ``plant_cov`` and ``mgt_ops`` should carry
their real per-row values rather than silently absorbing the multi-word
``"Original Simulation"`` description.

This guards against the silent mis-mapping regression detected in 7.3j:
pre-stripper, the existing text-merge branch folded the scenario
description tokens into ``plant_cov`` whenever the header included it
at the basin scale (even though in URU outputs ``plant_cov`` carries a
numeric code, not a string).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from swatplus_ai.parser.outputs.basin_wb_aa import parse_basin_wb_aa

_CORE_HEADER = (
    "jday mon day yr unit gis_id name "
    "precip snofall snomlt surq_gen latq wateryld perc "
    "et ecanopy eplant esoil surq_cont cn "
    "sw_init sw_final sw_ave sw_300 sno_init sno_final snopack "
    "pet qtile irr surq_runon latq_runon overbank "
    "surq_cha surq_res surq_ls latq_cha latq_res latq_ls "
    "gwsoilq satex satex_chan sw_change "
    "lagsurf laglatq lagsatex "
    "wet_evap wet_oflo wet_stor"
)
# 49 core tokens + plant_cov + mgt_ops = 51 declared columns.
_HEADER = f"{_CORE_HEADER} plant_cov mgt_ops"

# Unit row: 42 physical units (skipping the 7 id / text metadata cols +
# plant_cov / mgt_ops which have none) — shape follows the writer.
_UNIT_LINE = "---   mo  d   yr  -    -     -    " + " ".join(["mm"] * 42)

# 49 core values + 2 optional (plant_cov=1.234, mgt_ops=5) + 3 trailing
# scenario tokens (Original Simulation 0.000) = 54 tokens total.
_CORE_VALUES = "365  12  31  1989 1    1     basin " + " ".join(["0.1"] * 42)
_DATA_LINE = f"{_CORE_VALUES} 1.234 5 Original Simulation 0.000"


def _write_uru_validation_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "basin_wb_aa.txt"
    p.write_text(
        f"synthetic_uru_validation SWAT+ 2026.61.0.2\n{_HEADER}\n{_UNIT_LINE}\n{_DATA_LINE}\n"
    )
    return p


def test_uru_shape_strips_trailing_and_preserves_optional_values(tmp_path: Path) -> None:
    """51-col header + 54-token row strips cleanly and keeps real plant_cov/mgt_ops."""
    path = _write_uru_validation_fixture(tmp_path)
    df = parse_basin_wb_aa(path)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert len(df.columns) == 51

    row = df.iloc[0]
    assert row["name"] == "basin"
    assert row["precip"] == pytest.approx(0.1)
    assert row["wet_stor"] == pytest.approx(0.1)
    # ``plant_cov`` and ``mgt_ops`` are classified as text columns
    # (HRU scope writes land-use codes there); URU happens to write
    # numeric values, so we compare against the on-disk string form.
    assert row["plant_cov"] == "1.234"
    assert row["mgt_ops"] == "5"


def test_uru_shape_trailing_does_not_bleed_into_plant_cov(tmp_path: Path) -> None:
    """Scenario description must not land in ``plant_cov`` — the whole point of 7.3j."""
    path = _write_uru_validation_fixture(tmp_path)
    df = parse_basin_wb_aa(path)

    row = df.iloc[0]
    assert row["plant_cov"] != "Original Simulation"
    assert row["plant_cov"] != "Original"
    assert "Simulation" not in str(row["plant_cov"])
