"""Tests for the ``swatplus-ai telemetry`` sub-app."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from swatplus_ai.telemetry import config
from swatplus_ai.telemetry.cli import app


def _run(args: list[str]) -> object:
    return CliRunner().invoke(app, args)


def test_status_reports_enabled_by_default(isolated_home: Path) -> None:
    result = _run(["status"])
    assert result.exit_code == 0
    assert "telemetry: enabled" in result.stdout
    assert str(config.config_path()) in result.stdout


def test_status_reports_env_disabled(isolated_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(config.ENV_DISABLE, "1")
    result = _run(["status"])
    assert result.exit_code == 0
    assert f"telemetry: disabled via {config.ENV_DISABLE}" in result.stdout


def test_status_reports_config_disabled(isolated_home: Path) -> None:
    config.set_enabled(False)
    result = _run(["status"])
    assert result.exit_code == 0
    assert "telemetry: disabled" in result.stdout


def test_enable_persists(isolated_home: Path) -> None:
    config.set_enabled(False)
    result = _run(["enable"])
    assert result.exit_code == 0
    assert "telemetry: enabled" in result.stdout
    assert config.is_enabled() is True


def test_disable_persists(isolated_home: Path) -> None:
    result = _run(["disable"])
    assert result.exit_code == 0
    assert "telemetry: disabled" in result.stdout
    assert config.is_enabled() is False


def test_no_args_shows_help(isolated_home: Path) -> None:
    result = _run([])
    # Typer sub-apps with ``no_args_is_help`` exit 0 after printing help.
    assert result.exit_code in (0, 2)
    assert "status" in result.stdout
    assert "enable" in result.stdout
    assert "disable" in result.stdout
