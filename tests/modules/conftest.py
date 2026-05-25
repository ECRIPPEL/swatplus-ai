"""Shared fixtures for the ``swatplus_ai.modules`` test package.

Three isolation concerns repeat across every test in here, so they live
once as autouse / module-scoped fixtures:

* ``reset_telemetry_state`` — the telemetry module keeps process-wide
  state (default sink, session id, pre-configure buffer, one-shot
  failure flag). Without a per-test reset, whichever test ran first
  would own the session id for the rest of the run.
* ``no_real_retrieval`` — short-circuits the grounding layer's
  retrieval step so no module test accidentally hits the gitbook
  fetcher or the BM25 cache on disk. Tests that want specific retrieved
  passages re-patch :func:`swatplus_ai.prompts.grounding.retrieve_passages_for_findings`
  in their own body (later ``monkeypatch.setattr`` wins).
* ``isolated_home`` / ``enable_telemetry`` — mirror the helpers under
  ``tests/telemetry/`` so setup-check tests don't touch the real user
  config and don't silently fall into ``is_enabled()=False`` when an
  env var is set in CI.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

import swatplus_ai.telemetry as telemetry
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.prompts.builder import StaticPassage

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_telemetry_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telemetry, "_DEFAULT_SINK", None)
    monkeypatch.setattr(telemetry, "_SESSION_ID", None)
    monkeypatch.setattr(telemetry, "_BUFFER", deque(maxlen=telemetry._BUFFER_MAXLEN))
    monkeypatch.setattr(telemetry, "_SINK_FAILURE_WARNED", False)


@pytest.fixture(autouse=True)
def no_real_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default-patch the grounding retrieval step to return no passages.

    ``build_grounded_module1_prompt`` calls
    :func:`retrieve_passages_for_findings` by module-local name, so a
    single ``monkeypatch.setattr`` of that attribute is enough to fully
    short-circuit retrieval in every LLM-path test (no network, no BM25
    index build, no cache dir churn). Tests that want specific passages
    flowing through the formatter re-patch the same attribute — pytest's
    ``monkeypatch`` undoes in LIFO order so the per-test patch overrides
    this default for the duration of the test only.
    """

    def _empty(
        findings: Sequence[Finding],
        **_kwargs: Any,
    ) -> tuple[StaticPassage, ...]:
        del findings
        return ()

    monkeypatch.setattr("swatplus_ai.prompts.grounding.retrieve_passages_for_findings", _empty)


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
