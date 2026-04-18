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
    """A ``TxtInOutProject`` with every bundled rule satisfied.

    The committed minimal fixture is faithful to the SWAT+ file grammar
    but is not an internally-consistent project. Five classes of drift
    fire bundled rules on the raw fixture, so we ``model_copy`` each
    one — leaving the on-disk files untouched so other parser tests
    keep pinning the exact bytes they were written against:

    * **Slice 4.2:** warm-up ratio (``nyskip=1, span=2`` → 0.50);
      ``object.cnt.res=0`` but ``reservoir.con`` lists one row.
    * **Slice 4.3:** ``codes.bsn.pet=1`` (Penman-Monteith) would fire
      ``setup.pet_method_vs_climate`` because every station has
      ``slr/hmd/wnd = sim``; the two HRU rows reference ``soil=soil1``
      which isn't in ``soils.sol``; the single ``chandeg.con`` row is a
      self-loop (``cha001 → cha001``) with ``out_tot=1`` and no outfall;
      ``pcp.cli`` lists filenames that don't exist on disk.
    """
    project = TxtInOutProject.read(minimal_project)
    fixed_time = project.time_sim.model_copy(update={"yrc_end": 2009})
    fixed_print = project.print_prt.model_copy(update={"nyskip": 2})
    assert project.object_cnt is not None
    fixed_cnt = project.object_cnt.model_copy(update={"res": 1})
    # pet=3 (Hargreaves) only needs temperature, so the PET-vs-climate
    # rule treats it as vacuously satisfied and emits nothing.
    fixed_codes = project.codes_bsn.model_copy(update={"pet": 3})
    # Point both HRU rows at a soil name that actually exists in soils.sol.
    fixed_hru_rows = tuple(
        r.model_copy(update={"soil": "sandy_loam"}) for r in project.hru_data.rows
    )
    fixed_hru_data = project.hru_data.model_copy(update={"rows": fixed_hru_rows})
    # Convert the single cha001 row into a proper outfall: no connections,
    # out_tot=0 — satisfies outfall existence and avoids the self-loop
    # cycle detection branch.
    assert project.chandeg_con is not None
    clean_cha_row = project.chandeg_con.rows[0].model_copy(update={"out_tot": 0, "connections": ()})
    fixed_chandeg = project.chandeg_con.model_copy(update={"rows": (clean_cha_row,)})
    return project.model_copy(
        update={
            "time_sim": fixed_time,
            "print_prt": fixed_print,
            "object_cnt": fixed_cnt,
            "codes_bsn": fixed_codes,
            "hru_data": fixed_hru_data,
            "chandeg_con": fixed_chandeg,
            # pcp.cli lists station filenames (sta001.pcp, sta002.pcp,
            # sta003.pcp) that aren't present in the scrubbed fixture
            # directory — dropping the index tells wx.source_consistency
            # to skip that variable entirely.
            "pcp_cli": None,
        }
    )
