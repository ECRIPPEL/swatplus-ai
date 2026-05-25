"""Tests for :mod:`swatplus_ai.diagnostics.drift`.

Covers the DriftRegistry context-manager contract that per-file parsers
rely on to surface tool-bug / spec-divergence observations to the rule
engine. ``record_drift`` outside a scope is a no-op by design so test
helpers can import parsers without threading a registry through.
"""

from __future__ import annotations

import dataclasses

import pytest

from swatplus_ai.diagnostics.drift import (
    DriftRecord,
    DriftRegistry,
    current_registry,
    record_drift,
)


def _sample() -> DriftRecord:
    return DriftRecord(
        file="parameters.bsn",
        column="day_lag_max",
        observed="0.00000",
        expected_by_fortran="integer (basin_parms%day_lag_mx)",
        category="tool_bug",
        source_ref="https://github.com/swat-model/swatplus/blob/main/src/basin_module.f90",
        fixed_in_version="3.1.0",
    )


def test_record_is_frozen() -> None:
    rec = _sample()
    with pytest.raises(dataclasses.FrozenInstanceError):
        rec.file = "other.file"  # type: ignore[misc]


def test_record_outside_scope_is_noop() -> None:
    # No context-manager active — dropping a record must not raise.
    record_drift(_sample())
    assert current_registry() is None


def test_registry_collects_records() -> None:
    with DriftRegistry() as reg:
        record_drift(_sample())
        record_drift(
            DriftRecord(
                file="print.prt",
                column="crop_yld",
                observed="b",
                expected_by_fortran="a|y|b|n",
                category="spec_compliant",
                source_ref="https://example/ref",
            )
        )
    assert len(reg.all()) == 2


def test_registry_by_file_filters() -> None:
    with DriftRegistry() as reg:
        record_drift(_sample())
        record_drift(
            DriftRecord(
                file="print.prt",
                column="crop_yld",
                observed="b",
                expected_by_fortran="a|y|b|n",
                category="spec_compliant",
                source_ref="https://example/ref",
            )
        )
    assert len(reg.by_file("parameters.bsn")) == 1
    assert len(reg.by_file("print.prt")) == 1
    assert reg.by_file("nope.cio") == ()


def test_registry_by_category_filters() -> None:
    with DriftRegistry() as reg:
        record_drift(_sample())
        record_drift(
            DriftRecord(
                file="print.prt",
                column="crop_yld",
                observed="b",
                expected_by_fortran="a|y|b|n",
                category="spec_compliant",
                source_ref="https://example/ref",
            )
        )
    assert len(reg.by_category("tool_bug")) == 1
    assert len(reg.by_category("spec_compliant")) == 1
    assert reg.by_category("user_invalid") == ()


def test_registry_scope_pops_on_exit() -> None:
    assert current_registry() is None
    with DriftRegistry():
        assert current_registry() is not None
    assert current_registry() is None


def test_registry_scopes_nest() -> None:
    with DriftRegistry() as outer:
        record_drift(_sample())
        with DriftRegistry() as inner:
            record_drift(_sample())
            assert current_registry() is inner
        assert current_registry() is outer
    assert len(outer.all()) == 1
    assert len(inner.all()) == 1
