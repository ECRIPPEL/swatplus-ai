"""``swatplus-ai telemetry`` sub-app: status / enable / disable.

Three sibling commands so users can inspect and toggle the global flag
without hand-editing ``~/.swatplus-ai/config.toml``. ``status`` reports
three distinct states (env-disabled, config-disabled, enabled) because
the env-var override is frequently forgotten and troubleshooting a
silent log directory usually starts with "is the thing even on?".
"""

from __future__ import annotations

import os

import typer

from swatplus_ai.telemetry import config as _config

app = typer.Typer(
    name="telemetry",
    help="Inspect or change whether SWAT+ai writes local interaction logs.",
    no_args_is_help=True,
)


@app.command("status")
def status() -> None:
    """Report whether telemetry is currently enabled."""
    path = _config.config_path()
    if os.environ.get(_config.ENV_DISABLE) == "1":
        typer.echo(f"telemetry: disabled via {_config.ENV_DISABLE}")
        return
    if _config.is_enabled():
        typer.echo(f"telemetry: enabled (config: {path})")
    else:
        typer.echo(f"telemetry: disabled (config: {path})")


@app.command("enable")
def enable() -> None:
    """Turn telemetry on and persist the choice to the user config."""
    _config.set_enabled(True)
    typer.echo(f"telemetry: enabled (config: {_config.config_path()})")


@app.command("disable")
def disable() -> None:
    """Turn telemetry off and persist the choice to the user config."""
    _config.set_enabled(False)
    typer.echo(f"telemetry: disabled (config: {_config.config_path()})")


__all__ = ["app"]
