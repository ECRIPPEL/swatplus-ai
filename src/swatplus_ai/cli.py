"""Command-line entry point for SWAT+ai."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from swatplus_ai import __version__, telemetry
from swatplus_ai.config_cli import _default_store, _key_name
from swatplus_ai.config_cli import app as config_app
from swatplus_ai.llm.backends.api_key import AnthropicBackend, OpenAIBackend
from swatplus_ai.llm.backends.mock import MockBackend
from swatplus_ai.llm.interface import LLMBackend, LLMError
from swatplus_ai.llm.tokens import TokenStore
from swatplus_ai.modules import SetupCheckResult, render_setup_check_result, run_setup_check
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
app.add_typer(config_app, name="config")

_PROVIDER_CHOICES: tuple[str, ...] = ("anthropic", "openai", "mock")


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


def _resolve_store() -> TokenStore | None:
    """Best-effort token-store access for auto-detect.

    A missing ``keyring`` install must *not* crash ``swatplus-ai check``
    — the CLI will simply fall back to MockBackend and tell the user
    how to wire credentials. ``LLMError`` is the documented signal for
    "keyring optional dep isn't installed".
    """
    try:
        return _default_store()
    except LLMError:
        return None


def _lookup_key(store: TokenStore | None, provider: str) -> str | None:
    if store is None:
        return None
    return store.get(_key_name(provider))


def _select_backend(
    provider: str | None,
    *,
    skip_llm: bool,
    console: Console,
) -> LLMBackend:
    """Pick a backend based on the explicit flag + configured keys.

    Resolution order when ``provider`` is ``None``: anthropic first
    (default is Haiku, the cheaper option), then openai, finally
    ``MockBackend`` with a console warning so the user knows the
    response won't be useful but the pipeline will still render.

    When ``provider`` is explicit, missing credentials are a hard exit
    (code 1) with a concrete remediation hint — silently downgrading an
    explicit provider to mock would hide a misconfiguration.
    """
    if skip_llm or provider == "mock":
        return MockBackend()
    store = _resolve_store()
    if provider in ("anthropic", "openai"):
        key = _lookup_key(store, provider)
        if not key:
            console.print(
                f"[bold red]no {provider} key configured.[/bold red] "
                f"run [cyan]swatplus-ai config set-key {provider} <key>[/cyan] and retry."
            )
            raise typer.Exit(code=1)
        if provider == "anthropic":
            return AnthropicBackend(api_key=key)
        return OpenAIBackend(api_key=key)
    # Auto-detect.
    anthropic_key = _lookup_key(store, "anthropic")
    if anthropic_key:
        return AnthropicBackend(api_key=anthropic_key)
    openai_key = _lookup_key(store, "openai")
    if openai_key:
        return OpenAIBackend(api_key=openai_key)
    console.print(
        "[yellow]no credentials configured — falling back to MockBackend. "
        "run [cyan]swatplus-ai config set-key <provider> <key>[/cyan] to wire a real provider.[/yellow]"
    )
    return MockBackend()


def _provider_callback(value: str | None) -> str | None:
    """Validate the ``--provider`` value; typer maps a BadParameter to exit 2."""
    if value is None:
        return value
    normalized = value.strip().lower()
    if normalized not in _PROVIDER_CHOICES:
        raise typer.BadParameter(
            f"unknown provider {value!r}; expected one of {', '.join(_PROVIDER_CHOICES)}"
        )
    return normalized


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
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="anthropic | openai | mock. Default: auto-detect from configured keys.",
        callback=_provider_callback,
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help="Model id. Default: backend's built-in default.",
    ),
    stream: bool = typer.Option(
        True,
        "--stream/--no-stream",
        help="Stream the LLM response token-by-token (default on).",
    ),
) -> None:
    """Run Module 1's setup diagnostic on a SWAT+ project.

    Boots per-session telemetry (``session_start`` / ``session_end``
    bracket the run, ``user_action`` records the CLI invocation), parses
    the project, runs the bundled rule set, optionally calls the LLM,
    and renders the result to the terminal.
    """
    session_id = telemetry.start_session(_session_sink_factory)
    telemetry.emit(
        "session_start",
        command="check",
        project_path=str(path),
        skip_llm=skip_llm,
        provider=provider,
        model=model,
        stream=stream,
    )
    console = Console()
    exit_code = 0
    try:
        backend = _select_backend(provider, skip_llm=skip_llm, console=console)
        result = asyncio.run(
            _run_check_with_optional_live(
                path=path,
                backend=backend,
                skip_llm=skip_llm,
                stream=stream,
                model=model,
                console=console,
            )
        )
        render_setup_check_result(result, console)
    except typer.Exit:
        exit_code = 1
        raise
    except Exception as exc:
        exit_code = 1
        console.print(f"[bold red]check failed:[/bold red] {exc}")
    finally:
        telemetry.emit("user_action", command="check", exit_code=exit_code)
        telemetry.emit("session_end", command="check", exit_code=exit_code)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
    typer.echo(f"session: {session_id}")


@app.command()
def serve(
    path: Path = typer.Argument(  # noqa: B008
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Path to a SWAT+ TxtInOut/ project folder.",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Bind address. Default 127.0.0.1 — localhost-only. Pass 0.0.0.0 at your own risk.",
    ),
    port: int = typer.Option(
        8765,
        "--port",
        help="TCP port. Default 8765; vite dev proxy expects this value.",
    ),
    static_dir: Path | None = typer.Option(  # noqa: B008
        None,
        "--static-dir",
        help="Directory with a built UI bundle (e.g. ui/dist/) to mount at /.",
    ),
) -> None:
    """Serve the UI API from a SWAT+ project folder.

    Starts a local FastAPI server exposing ``/api/project``,
    ``/api/findings``, and ``/api/landuse`` against the parsed project.
    Endpoints the UI needs but the backend can't populate yet return
    HTTP 501 — the UI renders a graceful placeholder.

    FastAPI and uvicorn are optional deps; if they're missing the
    command exits with an install hint (``pip install 'swatplus-ai[serve]'``)
    rather than a raw ``ModuleNotFoundError``.
    """
    try:
        import uvicorn

        from swatplus_ai.api.server import create_app
    except ImportError as exc:
        typer.echo(
            "serve: fastapi/uvicorn not installed. "
            "run `pip install 'swatplus-ai[serve]'` and retry.",
            err=True,
        )
        raise typer.Exit(code=1) from exc

    app_instance = create_app(path, static_dir=static_dir)
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


async def _run_check_with_optional_live(
    *,
    path: Path,
    backend: LLMBackend,
    skip_llm: bool,
    stream: bool,
    model: str | None,
    console: Console,
) -> SetupCheckResult:
    """Thin wrapper that binds a Rich ``Live`` panel to streamed deltas.

    Kept as a function (rather than inlined) so the ``check`` command
    stays linear and testable — tests that want to exercise streaming
    can call :func:`run_setup_check` directly without the ``Live``
    dance.
    """
    if skip_llm or not stream:
        return await run_setup_check(
            path, backend=backend, skip_llm=skip_llm, stream=False, model=model
        )
    buffer = Text()
    panel = Panel(buffer, title="LLM response (streaming…)", border_style="green")
    with Live(panel, console=console, refresh_per_second=12, transient=True) as live:

        def _on_delta(chunk: str) -> None:
            buffer.append(chunk)
            live.update(panel)

        return await run_setup_check(
            path,
            backend=backend,
            skip_llm=False,
            stream=True,
            on_delta=_on_delta,
            model=model,
        )


if __name__ == "__main__":
    app()
