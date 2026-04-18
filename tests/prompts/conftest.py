"""Shared fixtures for the prompt-assembler tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.prompts.builder import ProjectSummary, StaticPassage

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def minimal_project_path() -> Path:
    """Committed synthetic SWAT+ project used by ``from_project`` tests."""
    return FIXTURES_DIR / "txtinout_minimal"


@pytest.fixture
def summary() -> ProjectSummary:
    """A fully-populated project summary for rendering tests."""
    return ProjectSummary(
        sim_start_year=2001,
        sim_end_year=2010,
        warmup_years=2,
        n_hrus=12,
        n_channels=3,
        n_aquifers=2,
        n_subbasins=3,
        pet_method=1,
        basin_area_km2=45.2,
    )


@pytest.fixture
def error_a() -> Finding:
    return Finding(
        id="setup.files_present",
        severity="error",
        location=None,
        evidence={"missing": ["time.sim"]},
        rule_ref="setup.files_present",
        message="Required file missing: time.sim",
        references=("swatplus_io_spec",),
    )


@pytest.fixture
def error_b() -> Finding:
    return Finding(
        id="chan.routing_topology",
        severity="error",
        location="chandeg.con:cha003",
        evidence={"cycle": ["cha003", "cha003"]},
        rule_ref="chan.routing_topology",
        message="Self-loop detected on cha003",
        references=(),
    )


@pytest.fixture
def warning_a() -> Finding:
    return Finding(
        id="setup.warmup_ratio",
        severity="warning",
        location=None,
        evidence={"ratio": 0.5},
        rule_ref="setup.warmup_ratio",
        message="Warm-up is 50% of the simulation span",
        references=("plunge_2024",),
    )


@pytest.fixture
def passage_a() -> StaticPassage:
    return StaticPassage(
        id="swatplus_io_spec.time_sim",
        title="time.sim — simulation period",
        body="Defines start and end of the simulation window as Julian day / year.",
        source="SWAT+ I/O spec v60.5.7",
    )


@pytest.fixture
def passage_b() -> StaticPassage:
    return StaticPassage(
        id="plunge_2024.warmup",
        title="SWATdoctR — warm-up guidance",
        body="Plunge (2024) recommends at least 3 years of warm-up on humid basins.",
        source="Plunge 2024, Env Modelling & Software",
    )
