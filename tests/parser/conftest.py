"""Shared fixtures for parser tests."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(scope="session")
def minimal_project() -> Path:
    """Path to the committed, synthetic minimal SWAT+ project.

    Always present in the repo — used to validate parser logic in CI.
    """
    return FIXTURES_DIR / "txtinout_minimal"


@pytest.fixture(scope="session")
def uru_project() -> Path:
    """Path to the private URU SWAT+ fixture (gitignored).

    Skips any test that depends on it when the folder is absent — so a
    fresh clone or CI run stays green without the real data.
    """
    d = FIXTURES_DIR / "txtinout_uru_min"
    if not d.is_dir():
        pytest.skip("private URU fixture not available (optional, local dev only)")
    return d
