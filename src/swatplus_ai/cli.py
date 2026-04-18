"""Command-line entry point for SWAT+ai."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

from swatplus_ai import __version__, telemetry
from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.interface import LLMBackend
from swatplus_ai.modules import render_setup_check_result, run_setup_check
from swatplus_ai.telemetry.cli import app as telemetry_app
from swatplus_ai.telemetry.logs import default_logs_dir
from swatplus_ai.telemetry.logs_cli import app as logs_app
from swatplus_ai.telemetry.sinks import JsonlFileSink, NullSink, Sink

app = typer.Typer(
    name="swatplus-ai",
    help="AI assistant for SWAT+ model setup, calibration, and evaluation.",
    no_args_is_help=True,
)
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(logs_app, name="logs")


@app.command()
def version() -> None:
    """Print the installed SWAT+ai version."""
    typer.echo(f"swatplus-ai {__version__}")


@app.command()
def chat() -> None:
    """Start an interactive chat session (not yet implemented)."""
    typer.echo("chat: not yet implemented")
    raise typer.Exit(code=1)


def _session_sink_factory(session_id: str) -> Sink:
    """Build the production ``JsonlFileSink`` for a new session id.

    Respects the telemetry toggle: when the user has disabled logging
    (``telemetry disable`` or ``SWATPLUS_AI_NO_LOG=1``), no file is
    created — emission is a no-op, but we still return a sink so the
    rest of the CLI doesn't branch on whether telemetry is on.
    """
    if not telemetry.is_enabled():
        return NullSink()
    path = default_logs_dir() / f"session-{session_id}.jsonl"
    return JsonlFileSink(path)


def _build_backend(skip_llm: bool) -> LLMBackend:
    """Pick a backend for the run.

    Until ``swatplus-ai config set-key`` lands in slice 7.2, the only
    wired backend is :class:`MockBackend` — it echoes the last user
    message, which is enough to prove the end-to-end wiring works and
    to dogfood the prompt/response pipeline. With ``--skip-llm`` the
    backend is still constructed (``run_setup_check`` never calls it)
    so the CLI remains one-branch.
    """
    del skip_llm
    return MockBackend()


@app.command()
def check(
    path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Path to a SWAT+ TxtInOut/ project folder.",
    ),
    skip_llm: bool = typer.Option(
        False,
        "--skip-llm",
        help="Run rules + render only; do not dispatch any LLM call.",
    ),
) -> None:
    """Run Module 1's setup diagnostic on a SWAT+ project.

    Boots per-session telemetry (``session_start`` / ``session_end``
    bracket the run, ``user_action`` records the CLI invocation), parses
    the project, runs the bundled rule set, optionally calls the LLM
    through :class:`MockBackend` (until real backends are keyed in
    slice 7.2), and renders the result to the terminal.
    """
    session_id = telemetry.start_session(_session_sink_factory)
    telemetry.emit(
        "session_start",
        command="check",
        project_path=str(path),
        skip_llm=skip_llm,
    )
    exit_code = 0
    try:
        backend = _build_backend(skip_llm)
        result = asyncio.run(
            run_setup_check(path, backend=backend, skip_llm=skip_llm),
        )
        console = Console()
        render_setup_check_result(result, console)
    except Exception as exc:
        exit_code = 1
        Console().print(f"[bold red]check failed:[/bold red] {exc}")
    finally:
        telemetry.emit(
            "user_action",
            command="check",
            exit_code=exit_code,
        )
        telemetry.emit("session_end", command="check", exit_code=exit_code)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
    typer.echo(f"session: {session_id}")


if __name__ == "__main__":
    app()
