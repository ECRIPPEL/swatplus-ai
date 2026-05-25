"""Tests for ``swatplus_ai.parser.inputs.pesticide_pes``."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics.drift import DriftRegistry
from swatplus_ai.parser._base import ParseError
from swatplus_ai.parser.inputs.pesticide_pes import PesticidePes, parse_pesticide_pes

_BASELINE_HEADER = (
    "name soil_ads frac_wash hl_foliage hl_soil solub aq_hlife aq_volat mol_wt "
    "aq_resus aq_settle ben_act_dep ben_bury ben_hlife description"
)
_BASELINE_ROW = "245-tp 2600 0.4 5 20 2.5 0.007 0.00001 0.1 0.002 0.5 0.3 0.002 0.05 Silvex_Amine"


def test_parse_minimal(minimal_project: Path) -> None:
    p = parse_pesticide_pes(minimal_project / "pesticide.pes")
    assert isinstance(p, PesticidePes)
    assert len(p.rows) == 2
    first = p.by_name("245-tp")
    assert first is not None
    assert first.soil_ads == pytest.approx(2600.0)
    assert first.solub == pytest.approx(2.5)
    assert first.description == "Silvex_Amine"
    assert p.rows[1].description is None


def test_missing_required_column_raises(tmp_path: Path) -> None:
    p = tmp_path / "pesticide.pes"
    p.write_text(
        "pesticide.pes: synthetic\n"
        "name NOPE frac_wash hl_foliage hl_soil solub aq_hlife aq_volat mol_wt "
        "aq_resus aq_settle ben_act_dep ben_bury ben_hlife description\n"
        "245-tp 2600 0.4 5 20 2.5 0.007 0.00001 0.1 0.002 0.5 0.3 0.002 0.05 desc\n"
    )
    with pytest.raises(ParseError, match="missing expected column"):
        parse_pesticide_pes(p)


def test_too_few_tokens_raises(tmp_path: Path) -> None:
    p = tmp_path / "pesticide.pes"
    p.write_text(f"pesticide.pes: synthetic\n{_BASELINE_HEADER}\n245-tp 2600 0.4 5 20 2.5\n")
    with pytest.raises(ParseError, match="expected at least 14 tokens"):
        parse_pesticide_pes(p)


def test_baseline_header_records_no_drift(tmp_path: Path) -> None:
    p = tmp_path / "pesticide.pes"
    p.write_text(f"pesticide.pes: synthetic\n{_BASELINE_HEADER}\n{_BASELINE_ROW}\n")
    with DriftRegistry() as reg:
        parse_pesticide_pes(p)
    assert reg.all() == ()


def test_pl_uptake_extra_column_parsed_and_drift_recorded(tmp_path: Path) -> None:
    """Editor v3.x writes ``pl_uptake`` between ``ben_hlife`` and ``description``.

    Permissive header mode tolerates the extra column and records a
    ``DriftRecord(category="unknown_column")`` rather than crashing the
    parse. Known-column values (soil_ads, ben_hlife, description) still
    map correctly because row reads use the name-based index map.
    """
    p = tmp_path / "pesticide.pes"
    extended_header = (
        "name soil_ads frac_wash hl_foliage hl_soil solub aq_hlife aq_volat mol_wt "
        "aq_resus aq_settle ben_act_dep ben_bury ben_hlife pl_uptake description"
    )
    # 16 tokens — same order as extended header, pl_uptake=0.01 between ben_hlife and desc
    extended_row = (
        "245-tp 2600 0.4 5 20 2.5 0.007 0.00001 0.1 0.002 0.5 0.3 0.002 0.05 0.01 Silvex_Amine"
    )
    p.write_text(f"pesticide.pes: synthetic\n{extended_header}\n{extended_row}\n")

    with DriftRegistry() as reg:
        parsed = parse_pesticide_pes(p)

    row = parsed.by_name("245-tp")
    assert row is not None
    # Known-column values still map correctly despite the inserted extra column.
    assert row.soil_ads == pytest.approx(2600.0)
    assert row.ben_hlife == pytest.approx(0.05)
    assert row.description == "Silvex_Amine"

    drifts = reg.by_file("pesticide.pes")
    assert len(drifts) == 1
    drift = drifts[0]
    assert drift.category == "unknown_column"
    assert drift.column == "pl_uptake"
    assert drift.observed == "0.01"
    assert drift.source_ref == "<pending>"


def test_malformed_float_in_known_column_raises(tmp_path: Path) -> None:
    """Guardrail: permissive mode only accepts EXTRA columns, not BAD values."""
    p = tmp_path / "pesticide.pes"
    bad_row = "245-tp NOT_A_NUMBER 0.4 5 20 2.5 0.007 0.00001 0.1 0.002 0.5 0.3 0.002 0.05 desc"
    p.write_text(f"pesticide.pes: synthetic\n{_BASELINE_HEADER}\n{bad_row}\n")
    with pytest.raises(ParseError, match="expected float for 'soil_ads'"):
        parse_pesticide_pes(p)
