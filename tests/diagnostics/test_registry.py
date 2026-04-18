"""Tests for ``swatplus_ai.diagnostics.registry``."""

from __future__ import annotations

import pytest

from swatplus_ai.diagnostics import CheckResult, register_check
from swatplus_ai.diagnostics.registry import get_check


def test_register_and_lookup(clean_registry: None) -> None:
    @register_check("_test_registry_ok")
    def _fn(project: object) -> CheckResult:
        return CheckResult(location="x", evidence={"a": 1})

    fn = get_check("_test_registry_ok")
    result = fn(object())  # type: ignore[arg-type]
    assert isinstance(result, CheckResult)
    assert result.location == "x"
    assert result.evidence == {"a": 1}


def test_duplicate_registration_raises(clean_registry: None) -> None:
    @register_check("_test_registry_dup")
    def _fn(project: object) -> None:
        return None

    with pytest.raises(ValueError, match="already registered"):

        @register_check("_test_registry_dup")
        def _fn2(project: object) -> None:
            return None


def test_missing_lookup_raises() -> None:
    with pytest.raises(KeyError, match="No check registered"):
        get_check("_test_registry_nonexistent")


def test_check_result_defaults() -> None:
    cr = CheckResult()
    assert cr.location is None
    assert cr.evidence == {}


def test_check_result_is_frozen() -> None:
    cr = CheckResult(location="loc", evidence={"k": 1})
    with pytest.raises(Exception):  # noqa: B017 — pydantic raises ValidationError
        cr.location = "other"  # type: ignore[misc]
