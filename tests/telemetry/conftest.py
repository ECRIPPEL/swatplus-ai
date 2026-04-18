"""Shared fixtures for telemetry tests.

Two kinds of isolation matter here:

* ``reset_telemetry_state`` — the telemetry module keeps a process-wide
  default sink, a lazy session id, a pre-configure buffer, and a
  one-shot failure flag. Tests must start from a known state; without
  that, whichever test ran first would own the session id for the rest
  of the run.
* ``isolated_home`` — the config layer reads and writes
  ``~/.swatplus-ai/config.toml``. Tests must never touch the real user
  config, so we redirect ``Path.home()`` into ``tmp_path`` and clear
  ``XDG_CONFIG_HOME`` / ``SWATPLUS_AI_NO_LOG``.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

import pytest

import swatplus_ai.telemetry as telemetry


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
    """Force :func:`config.is_enabled` to return True regardless of env/config."""

    def _always_enabled(*_args: Any, **_kwargs: Any) -> bool:
        return True

    monkeypatch.setattr("swatplus_ai.telemetry.config.is_enabled", _always_enabled)
