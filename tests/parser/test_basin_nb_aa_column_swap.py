"""Regression tests for name-based column mapping in ``basin_nb_aa``.

These tests pin the behaviour added in slice 7.3k: the parser reconciles
canonical and on-disk header *by name*, so reordered headers — e.g. the
``nuptake`` / ``puptake`` swap observed between SWAT+ simulator revs
2024 and 2026 — parse to the same DataFrame shape with values landing
in the canonical column regardless of writer order. Missing optional
tail columns (Rev 2024 basin-scale output without ``plant_cov`` /
``mgt_ops``) parse cleanly and are absent from the DataFrame rather
than NaN-filled or raising.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics.drift import DriftRegistry
from swatplus_ai.parser.outputs.basin_nb_aa import parse_basin_nb_aa

# Canonical order (as declared in the module's ``_CORE_HEADER``).
_CANONICAL_HEADER = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "grzn", "grzp", "lab_min_p", "act_sta_p",
    "fertn", "fertp", "fixn", "denit",
    "act_nit_n", "act_sta_n", "org_lab_p",
    "rsd_nitorg_n", "rsd_laborg_p",
    "no3atmo", "nh4atmo", "nuptake", "puptake",
    "gwsoiln", "gwsoilp",
)  # fmt: skip

# Swapped order: ``puptake`` appears before ``nuptake``. This emulates
# the difference seen between Rev 2026.61.0.2.61 and Rev 2024.61.0.2 in
# dogfood 2026-04-21.
_SWAPPED_HEADER = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
    "grzn", "grzp", "lab_min_p", "act_sta_p",
    "fertn", "fertp", "fixn", "denit",
    "act_nit_n", "act_sta_n", "org_lab_p",
    "rsd_nitorg_n", "rsd_laborg_p",
    "no3atmo", "nh4atmo", "puptake", "nuptake",   # <-- swapped
    "gwsoiln", "gwsoilp",
)  # fmt: skip


def _unit_row(n: int) -> str:
    return " ".join(["kg/ha"] * n)


def _synthetic_row(meta_tokens: tuple[str, ...], physical_values: tuple[str, ...]) -> str:
    """Build one data row + the 3-token trailing scenario block."""
    scenario = ("Original", "Simulation", "0.0")
    return " ".join(meta_tokens + physical_values + scenario)


def test_reordered_header_nuptake_puptake_values_follow_names(tmp_path: Path) -> None:
    """Swapped header — values must follow canonical names, not positions."""
    # Physicals keyed by canonical name. nuptake=77.7, puptake=11.1.
    values_by_name = {
        "grzn": "1.0",
        "grzp": "2.0",
        "lab_min_p": "3.0",
        "act_sta_p": "4.0",
        "fertn": "5.0",
        "fertp": "6.0",
        "fixn": "7.0",
        "denit": "8.0",
        "act_nit_n": "9.0",
        "act_sta_n": "10.0",
        "org_lab_p": "11.0",
        "rsd_nitorg_n": "12.0",
        "rsd_laborg_p": "13.0",
        "no3atmo": "14.0",
        "nh4atmo": "15.0",
        "nuptake": "77.7",
        "puptake": "11.1",
        "gwsoiln": "17.0",
        "gwsoilp": "18.0",
    }
    # Row follows the *swapped* header order, so puptake=11.1 comes
    # before nuptake=77.7 on disk.
    meta = ("365", "12", "31", "1989", "1", "1", "basin")
    physical_tokens = tuple(values_by_name[name] for name in _SWAPPED_HEADER[7:])

    p = tmp_path / "basin_nb_aa.txt"
    p.write_text(
        "synthetic_nb Rev 2024.61.0.2 - swapped nuptake/puptake\n"
        + " ".join(_SWAPPED_HEADER)
        + "\n"
        + _unit_row(len(_SWAPPED_HEADER) - 7)
        + "\n"
        + _synthetic_row(meta, physical_tokens)
        + "\n"
    )

    df = parse_basin_nb_aa(p)
    assert len(df) == 1
    row = df.iloc[0]
    # The proof: nuptake in the DataFrame matches the value that sat
    # under the ``nuptake`` header name, not under canonical position 22.
    assert row["nuptake"] == pytest.approx(77.7)
    assert row["puptake"] == pytest.approx(11.1)
    # Adjacent fields untouched.
    assert row["nh4atmo"] == pytest.approx(15.0)
    assert row["gwsoiln"] == pytest.approx(17.0)


def test_reordered_header_does_not_emit_drift(tmp_path: Path) -> None:
    """A legitimate rev-to-rev reorder is spec-compliant — no drift raised."""
    meta = ("365", "12", "31", "1989", "1", "1", "basin")
    physical_tokens = tuple(["0.0"] * (len(_SWAPPED_HEADER) - 7))
    p = tmp_path / "basin_nb_aa.txt"
    p.write_text(
        "synthetic_nb swapped\n"
        + " ".join(_SWAPPED_HEADER)
        + "\n"
        + _unit_row(len(_SWAPPED_HEADER) - 7)
        + "\n"
        + _synthetic_row(meta, physical_tokens)
        + "\n"
    )

    with DriftRegistry() as reg:
        parse_basin_nb_aa(p)
    assert reg.all() == ()


def test_rev2024_header_without_plant_cov_mgt_ops_parses(tmp_path: Path) -> None:
    """Rev 2024 basin output omits the optional tail — DataFrame omits them too."""
    meta = ("365", "12", "31", "1989", "1", "1", "basin")
    physical_tokens = tuple(["0.5"] * (len(_CANONICAL_HEADER) - 7))

    p = tmp_path / "basin_nb_aa.txt"
    p.write_text(
        "synthetic_nb Rev 2024 (no plant_cov/mgt_ops tail)\n"
        + " ".join(_CANONICAL_HEADER)
        + "\n"
        + _unit_row(len(_CANONICAL_HEADER) - 7)
        + "\n"
        + _synthetic_row(meta, physical_tokens)
        + "\n"
    )

    df = parse_basin_nb_aa(p)
    assert len(df) == 1
    # Optional tail absent from DataFrame entirely — not NaN-filled.
    assert "plant_cov" not in df.columns
    assert "mgt_ops" not in df.columns
    # Every core column present and populated.
    assert df.iloc[0]["fertn"] == pytest.approx(0.5)
    assert df.iloc[0]["nuptake"] == pytest.approx(0.5)


def test_rev2024_header_without_tail_does_not_emit_drift(tmp_path: Path) -> None:
    """Module-conditional optional absence must NOT be recorded as drift."""
    meta = ("365", "12", "31", "1989", "1", "1", "basin")
    physical_tokens = tuple(["0.0"] * (len(_CANONICAL_HEADER) - 7))
    p = tmp_path / "basin_nb_aa.txt"
    p.write_text(
        "synthetic_nb Rev 2024 no tail\n"
        + " ".join(_CANONICAL_HEADER)
        + "\n"
        + _unit_row(len(_CANONICAL_HEADER) - 7)
        + "\n"
        + _synthetic_row(meta, physical_tokens)
        + "\n"
    )

    with DriftRegistry() as reg:
        parse_basin_nb_aa(p)
    assert reg.all() == ()
