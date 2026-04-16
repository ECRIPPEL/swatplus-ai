"""Smoke tests — verify the package imports and the CLI responds."""

from __future__ import annotations

from typer.testing import CliRunner

from swatplus_ai import __version__
from swatplus_ai.cli import app


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


def test_cli_version_command() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
