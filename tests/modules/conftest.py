"""Shared fixtures for the ``swatplus_ai.modules`` test package.

Two isolation concerns repeat across every test in here, so they live
once as autouse / module-scoped fixtures:

* ``reset_telemetry_state`` — the telemetry module keeps process-wide
  state (default sink, session id, pre-configure buffer, one-shot
  failure flag). Without a per-test reset, whichever test ran first
  would own the session id for the rest of the run.
* ``isolated_home`` / ``enable_telemetry`` — mirror the helpers under
  ``tests/telemetry/`` so setup-check tests don't touch the real user
  config and don't silently fall into ``is_enabled()=False`` when an
  env var is set in CI.
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
    """Force ``telemetry.is_enabled`` to return True regardless of env/config."""

    def _always_enabled(*_args: Any, **_kwargs: Any) -> bool:
        return True

    monkeypatch.setattr("swatplus_ai.telemetry.config.is_enabled", _always_enabled)


@pytest.fixture(scope="session")
def minimal_project_path() -> Path:
    """Committed synthetic SWAT+ project used across module-1 orchestrator tests."""
    return FIXTURES_DIR / "txtinout_minimal"
