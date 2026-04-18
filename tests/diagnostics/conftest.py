"""Shared fixtures for the diagnostic-engine tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from swatplus_ai.diagnostics import registry

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
RULES_DIR = FIXTURES_DIR / "diagnostic_rules"


@pytest.fixture(scope="session")
def rule_fixtures_dir() -> Path:
    """Path to the committed synthetic rule YAML fixtures."""
    return RULES_DIR


@pytest.fixture(scope="session")
def minimal_project() -> Path:
    """Path to the committed, synthetic minimal SWAT+ project.

    Re-declared here (duplicate of the same-named fixture in
    ``tests/parser/conftest.py``) so diagnostic-engine tests can build
    a real :class:`TxtInOutProject` without pulling in ``tests.parser``.
    """
    return FIXTURES_DIR / "txtinout_minimal"


@pytest.fixture
def clean_registry() -> Iterator[None]:
    """Snapshot and restore the module-level check registry.

    Tests register synthetic checks at module load time; this fixture
    lets individual tests register / unregister without leaking state
    into later tests in the same session.
    """
    snapshot = dict(registry._CHECKS)
    try:
        yield
    finally:
        registry._CHECKS.clear()
        registry._CHECKS.update(snapshot)
