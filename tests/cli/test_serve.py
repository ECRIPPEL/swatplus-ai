"""Tests for ``swatplus-ai serve`` CLI wiring.

We can't actually start uvicorn inside pytest without either blocking
the test or leaking a port/thread — the things worth pinning here are:

* ``--help`` documents the flags (regression guard against a typer
  dropdown rename breaking the docs).
* With fastapi/uvicorn installed the command reaches ``uvicorn.run``
  and we can assert ``create_app`` was built with the right inputs.
* Without fastapi/uvicorn installed we exit 1 with a concrete install
  hint — a raw ``ModuleNotFoundError`` is bad UX.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from swatplus_ai.cli import app as root_app


def test_serve_help_lists_host_port_static_dir() -> None:
    runner = CliRunner()
    result = runner.invoke(root_app, ["serve", "--help"])
    assert result.exit_code == 0, result.output
    assert "--host" in result.output
    assert "--port" in result.output
    assert "--static-dir" in result.output


def test_serve_calls_uvicorn_run_with_create_app(
    minimal_project_path: Path,
) -> None:
    runner = CliRunner()
    captured: dict[str, Any] = {}

    def _fake_run(app_instance: Any, *, host: str, port: int, log_level: str) -> None:
        captured["app"] = app_instance
        captured["host"] = host
        captured["port"] = port
        captured["log_level"] = log_level

    import uvicorn

    with patch.object(uvicorn, "run", _fake_run):
        result = runner.invoke(
            root_app,
            [
                "serve",
                str(minimal_project_path),
                "--host",
                "127.0.0.1",
                "--port",
                "9999",
            ],
        )

    assert result.exit_code == 0, result.output
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 9999
    assert captured["log_level"] == "info"
    # The handed app should look like a FastAPI instance (has a `routes`
    # attribute) — a cheap structural check that avoids importing FastAPI
    # into the test when the module under test already did.
    assert hasattr(captured["app"], "routes")


def test_serve_exits_with_install_hint_when_fastapi_missing(
    minimal_project_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulate ``pip install swatplus-ai`` without the ``serve`` extra."""
    runner = CliRunner()

    real_import = __import__

    def _blocking_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "uvicorn" or name.startswith("swatplus_ai.api.server"):
            raise ImportError(f"blocked for test: {name}")
        return real_import(name, *args, **kwargs)

    # Evict any cached import so the ``try: import uvicorn`` path re-runs.
    monkeypatch.delitem(sys.modules, "uvicorn", raising=False)
    monkeypatch.delitem(sys.modules, "swatplus_ai.api.server", raising=False)
    monkeypatch.setattr("builtins.__import__", _blocking_import)

    result = runner.invoke(root_app, ["serve", str(minimal_project_path)])

    assert result.exit_code == 1
    # Typer prints stderr through Rich, which CliRunner merges into output.
    assert "swatplus-ai[serve]" in result.output
