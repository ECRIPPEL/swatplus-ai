"""Tests for ``swatplus_ai.diagnostics.finding.Finding``."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from swatplus_ai.diagnostics import Finding


def test_finding_construction() -> None:
    f = Finding(
        id="test.rule",
        severity="warning",
        location="hru-data.hru:row=42",
        evidence={"value": 0.31},
        rule_ref="test.rule",
        message="ET/precip ratio 0.31 is low.",
        references=("white_2014",),
    )
    assert f.id == "test.rule"
    assert f.severity == "warning"
    assert f.location == "hru-data.hru:row=42"
    assert f.evidence == {"value": 0.31}
    assert f.rule_ref == "test.rule"
    assert f.references == ("white_2014",)


def test_finding_is_frozen() -> None:
    f = Finding(
        id="test.rule",
        severity="info",
        location=None,
        evidence={},
        rule_ref="test.rule",
        message="nothing to see here",
    )
    with pytest.raises(ValidationError):
        f.id = "changed"  # type: ignore[misc]


def test_finding_rejects_extras() -> None:
    with pytest.raises(ValidationError):
        Finding(
            id="test.rule",
            severity="info",
            location=None,
            evidence={},
            rule_ref="test.rule",
            message="hi",
            extra_field="nope",  # type: ignore[call-arg]
        )


def test_finding_rejects_bad_severity() -> None:
    with pytest.raises(ValidationError):
        Finding(
            id="test.rule",
            severity="fatal",  # type: ignore[arg-type]
            location=None,
            evidence={},
            rule_ref="test.rule",
            message="hi",
        )


def test_finding_default_empty_references() -> None:
    f = Finding(
        id="test.rule",
        severity="info",
        location=None,
        evidence={},
        rule_ref="test.rule",
        message="hi",
    )
    assert f.references == ()
