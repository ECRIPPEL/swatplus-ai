"""Shared fixtures for ``swatplus-ai`` CLI tests.

Mirrors the isolation fixtures under ``tests/modules/`` so CLI tests
don't touch the user's real home, don't leak telemetry state into each
other, and — crucially — never reach the OS keychain.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import pytest

import swatplus_ai.telemetry as telemetry

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_telemetry_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telemetry, "_DEFAULT_SINK", None)
    monkeypatch.setattr(telemetry, "_SESSION_ID", None)
    monkeypatch.setattr(telemetry, "_BUFFER", deque(maxlen=telemetry._BUFFER_MAXLEN))
    monkeypatch.setattr(telemetry, "_SINK_FAILURE_WARNED", False)


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("SWATPLUS_AI_NO_LOG", raising=False)
    return tmp_path


@pytest.fixture
def enable_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    def _always_enabled(*_args: Any, **_kwargs: Any) -> bool:
        return True

    monkeypatch.setattr("swatplus_ai.telemetry.config.is_enabled", _always_enabled)


@pytest.fixture(scope="session")
def minimal_project_path() -> Path:
    return FIXTURES_DIR / "txtinout_minimal"
