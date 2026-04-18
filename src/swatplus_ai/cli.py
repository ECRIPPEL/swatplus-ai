"""Command-line entry point for SWAT+ai."""

from __future__ import annotations

import typer

from swatplus_ai import __version__
from swatplus_ai.telemetry.cli import app as telemetry_app

app = typer.Typer(
    name="swatplus-ai",
    help="AI assistant for SWAT+ model setup, calibration, and evaluation.",
    no_args_is_help=True,
)
app.add_typer(telemetry_app, name="telemetry")


@app.command()
def version() -> None:
    """Print the installed SWAT+ai version."""
    typer.echo(f"swatplus-ai {__version__}")


@app.command()
def chat() -> None:
    """Start an interactive chat session (not yet implemented)."""
    typer.echo("chat: not yet implemented")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
