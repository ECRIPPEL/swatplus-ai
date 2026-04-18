"""Shared fixtures for the diagnostic-engine tests."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from swatplus_ai.diagnostics import registry
from swatplus_ai.parser.txtinout import TxtInOutProject

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


@pytest.fixture
def clean_setup_project(minimal_project: Path) -> TxtInOutProject:
    """A ``TxtInOutProject`` with every bundled ``setup.*`` rule satisfied.

    The committed minimal fixture is faithful to the SWAT+ file grammar
    but is not an internally-consistent project: its warm-up ratio
    (nyskip=1, span=2 yrs → 0.50) and its ``object.cnt.res`` count
    (declared 0, but ``reservoir.con`` lists one row) both fire bundled
    rules. Rather than edit the fixture — other parser tests pin those
    exact values — we ``model_copy`` the three fields we need to change,
    leaving every other attribute untouched.
    """
    project = TxtInOutProject.read(minimal_project)
    fixed_time = project.time_sim.model_copy(update={"yrc_end": 2009})
    fixed_print = project.print_prt.model_copy(update={"nyskip": 2})
    assert project.object_cnt is not None
    fixed_cnt = project.object_cnt.model_copy(update={"res": 1})
    return project.model_copy(
        update={
            "time_sim": fixed_time,
            "print_prt": fixed_print,
            "object_cnt": fixed_cnt,
        }
    )
