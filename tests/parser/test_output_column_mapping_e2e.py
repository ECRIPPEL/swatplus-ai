"""End-to-end integration tests for name-based output column mapping.

Drives the whole ``read_aa_output_variable`` → ``map_columns_by_name`` →
``_build_dataframe`` chain through ``basin_nb_aa`` against three
synthetic fixtures the real-world dogfood (2026-04-21) surfaced as
distinct failure modes before slice 7.3k:

1. **Canonical** — header matches the schema 1:1. Proves the refactor
   didn't regress the happy path.
2. **Rev 2024 reordered + subset** — ``nuptake`` / ``puptake`` swapped
   and the optional ``plant_cov`` / ``mgt_ops`` tail absent. Proves
   the parser degrades gracefully across simulator revs without any
   drift emission.
3. **Unknown extra column** — header carries an ``xenriqueced`` token
   the canonical schema doesn't declare. Proves the parser emits a
   ``DriftRecord(category="unknown_column")`` per extra column rather
   than raising.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics.drift import DriftRegistry
from swatplus_ai.parser.outputs.basin_nb_aa import parse_basin_nb_aa

_CANONICAL_HEADER = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "grzn", "grzp", "lab_min_p", "act_sta_p",
    "fertn", "fertp", "fixn", "denit",
    "act_nit_n", "act_sta_n", "org_lab_p",
    "rsd_nitorg_n", "rsd_laborg_p",
    "no3atmo", "nh4atmo", "nuptake", "puptake",
    "gwsoiln", "gwsoilp",
)  # fmt: skip

_META = ("365", "12", "31", "1989", "1", "1", "basin")
_SCENARIO_BLOCK = ("Original", "Simulation", "0.0")


def _write_fixture(
    path: Path,
    *,
    title: str,
    header: tuple[str, ...],
    physical_values: tuple[str, ...],
) -> None:
    units = " ".join(["kg/ha"] * (len(header) - 7))
    row = " ".join(_META + physical_values + _SCENARIO_BLOCK)
    path.write_text(
        f"{title}\n{' '.join(header)}\n{units}\n{row}\n",
        encoding="utf-8",
    )


def test_canonical_fixture_parses_with_full_shape(tmp_path: Path) -> None:
    """Baseline — header matches schema 1:1, all columns present."""
    physicals = tuple(f"{i}.0" for i in range(1, len(_CANONICAL_HEADER) - 7 + 1))
    p = tmp_path / "basin_nb_aa.txt"
    _write_fixture(
        p, title="canonical Rev 2026", header=_CANONICAL_HEADER, physical_values=physicals
    )

    with DriftRegistry() as reg:
        df = parse_basin_nb_aa(p)

    assert len(df) == 1
    assert df.iloc[0]["nuptake"] == pytest.approx(16.0)  # 16th physical
    assert df.iloc[0]["puptake"] == pytest.approx(17.0)
    assert reg.all() == ()


def test_rev2024_reordered_subset_parses_without_drift(tmp_path: Path) -> None:
    """Rev 2024 style: nuptake/puptake swapped, optional tail absent."""
    swapped = (
        "jday", "mon", "day", "yr", "unit", "gis_id", "name",
        "grzn", "grzp", "lab_min_p", "act_sta_p",
        "fertn", "fertp", "fixn", "denit",
        "act_nit_n", "act_sta_n", "org_lab_p",
        "rsd_nitorg_n", "rsd_laborg_p",
        "no3atmo", "nh4atmo", "puptake", "nuptake",
        "gwsoiln", "gwsoilp",
    )  # fmt: skip
    # Same numeric order — so puptake=16 (at header pos 22), nuptake=17.
    physicals = tuple(f"{i}.0" for i in range(1, len(swapped) - 7 + 1))
    p = tmp_path / "basin_nb_aa.txt"
    _write_fixture(p, title="synthetic Rev 2024.61.0.2", header=swapped, physical_values=physicals)

    with DriftRegistry() as reg:
        df = parse_basin_nb_aa(p)

    assert len(df) == 1
    # Values follow canonical names, not positions — nuptake gets the
    # value that sat under the 'nuptake' token (pos 23 in this header).
    assert df.iloc[0]["nuptake"] == pytest.approx(17.0)
    assert df.iloc[0]["puptake"] == pytest.approx(16.0)
    # Optional tail absent — DataFrame omits the columns entirely.
    assert "plant_cov" not in df.columns
    assert "mgt_ops" not in df.columns
    # No drift: a module-conditional reorder is spec-compliant.
    assert reg.all() == ()


def test_unknown_extra_column_emits_drift_without_raising(tmp_path: Path) -> None:
    """Header carries a column the schema doesn't know — recorded as drift."""
    header_with_extra = (
        "jday", "mon", "day", "yr", "unit", "gis_id", "name",
        "grzn", "grzp", "lab_min_p", "act_sta_p",
        "fertn", "fertp", "fixn", "denit",
        "act_nit_n", "act_sta_n", "org_lab_p",
        "rsd_nitorg_n", "rsd_laborg_p",
        "no3atmo", "nh4atmo", "nuptake", "puptake",
        "gwsoiln", "gwsoilp",
        "xenriqueced",  # <-- extra, not in canonical
    )  # fmt: skip
    physicals = tuple(f"{i}.0" for i in range(1, len(header_with_extra) - 7 + 1))
    p = tmp_path / "basin_nb_aa.txt"
    _write_fixture(
        p,
        title="synthetic Rev 2026 with extra column",
        header=header_with_extra,
        physical_values=physicals,
    )

    with DriftRegistry() as reg:
        df = parse_basin_nb_aa(p)

    # Parser didn't raise; DataFrame has only canonical columns.
    assert "xenriqueced" not in df.columns
    # Drift registry captured the extra.
    records = reg.all()
    assert len(records) == 1
    (rec,) = records
    assert rec.column == "xenriqueced"
    assert rec.category == "unknown_column"
    assert rec.file == "basin_nb_aa.txt"
    # ``observed`` samples the token at the unknown position from the first row.
    assert rec.observed == "20.0"
