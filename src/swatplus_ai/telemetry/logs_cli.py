"""``swatplus-ai logs`` sub-app: list / show / export session logs.

Read-only counterpart to :mod:`swatplus_ai.telemetry.cli` (which toggles
the global flag). Production write-side wiring — calling
``configure(JsonlFileSink(...))`` at CLI boot — happens in Step 7 when
``swatplus-ai check <path>`` is introduced; until then, these commands
already work against any session file the test suite or a hand-wired
sink produces.

Three sibling commands:

* ``logs list`` — index of sessions under the current project's
  ``.swatplus-ai/logs/`` dir, newest first.
* ``logs show`` — pretty-print one session; defaults to the newest,
  ``--last N`` trims to the tail, ``--session UUID_PREFIX`` picks a
  specific one.
* ``logs export`` — byte-for-byte copy of one session's JSONL to a
  user-chosen path, aborting on overwrite.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from swatplus_ai.telemetry.events import Event
from swatplus_ai.telemetry.logs import (
    SessionSummary,
    default_logs_dir,
    find_sessions,
    load_session,
    resolve_session,
    session_id_from_path,
)

app = typer.Typer(
    name="logs",
    help="Inspect or export local SWAT+ai session logs.",
    no_args_is_help=True,
)

_SESSION_ID_PREVIEW = 8
_EMPTY_HINT = (
    "No session logs found in {path}. Run a check first (not yet available) "
    "or enable telemetry and re-run any command."
)


def _short(session_id: str) -> str:
    return session_id[:_SESSION_ID_PREVIEW]


def _format_started(summary: SessionSummary) -> str:
    if summary.started is None:
        return "—"
    return summary.started.isoformat(timespec="seconds")


def _summarize_event(event: Event) -> str:
    """Produce a short, human-readable summary of one event's payload.

    The chosen fields are those most useful at a glance for each event
    type — filename + rows + duration for parses, rule_id + count for
    engine events, etc. Anything we don't have a template for falls
    back to a plain ``key=value`` dump of the first few fields.
    """
    fields = event.fields
    kind = event.event_type
    if kind == "file_parsed":
        parts = [f"filename={fields.get('filename')!r}"]
        rows = fields.get("rows")
        if rows is not None:
            parts.append(f"rows={rows}")
        duration = fields.get("duration_ms")
        if duration is not None:
            parts.append(f"duration_ms={duration}")
        return " ".join(parts)
    if kind == "parse_error":
        parts = [
            f"filename={fields.get('filename')!r}",
            f"exception={fields.get('exception')}",
        ]
        if "line" in fields:
            parts.append(f"line={fields['line']}")
        return " ".join(parts)
    if kind == "rule_evaluated":
        parts = [f"rule_id={fields.get('rule_id')!r}"]
        if fields.get("skipped"):
            parts.append("skipped")
        else:
            parts.append(f"finding_count={fields.get('finding_count')}")
            parts.append(f"duration_ms={fields.get('duration_ms')}")
        return " ".join(parts)
    if kind == "finding_emitted":
        return f"rule_id={fields.get('rule_id')!r} severity={fields.get('severity')!r}"
    if kind in {"session_start", "session_end"}:
        # Any hand-picked fields a CLI booter bothered to attach.
        shown = list(fields.items())[:3]
        return " ".join(f"{k}={v!r}" for k, v in shown) or "—"
    if kind == "llm_call":
        parts = [f"model={fields.get('model')!r}"]
        if "latency_ms" in fields:
            parts.append(f"latency_ms={fields['latency_ms']}")
        return " ".join(parts)
    if kind == "llm_tool_call_chosen":
        return f"tool={fields.get('tool_name')!r}"
    if kind == "user_action":
        parts = [f"command={fields.get('command')!r}"]
        if "exit_code" in fields:
            parts.append(f"exit_code={fields['exit_code']}")
        return " ".join(parts)
    shown = list(fields.items())[:3]
    return " ".join(f"{k}={v!r}" for k, v in shown) or "—"


def _format_time_absolute(event: Event) -> str:
    """Format an event timestamp as absolute ``HH:MM:SS.mmm`` (UTC)."""
    ts = event.timestamp
    ms = ts.microsecond // 1000
    return f"{ts.strftime('%H:%M:%S')}.{ms:03d}"


@app.command("list")
def list_sessions() -> None:
    """List every session log in ``.swatplus-ai/logs/``, newest first."""
    logs_dir = default_logs_dir()
    sessions = find_sessions(logs_dir)
    if not sessions:
        typer.echo(_EMPTY_HINT.format(path=logs_dir))
        return
    console = Console()
    table = Table(title=f"Session logs in {logs_dir}")
    table.add_column("session_id", style="cyan", no_wrap=True)
    table.add_column("started", style="green")
    table.add_column("events", justify="right")
    table.add_column("file")
    for summary in sessions:
        table.add_row(
            _short(summary.session_id),
            _format_started(summary),
            str(summary.event_count),
            summary.path.name,
        )
    console.print(table)


@app.command("show")
def show_session(
    last: int | None = typer.Option(
        None,
        "--last",
        help="Show only the last N events (combinable with --session).",
    ),
    session: str | None = typer.Option(
        None,
        "--session",
        help="Select a session by uuid prefix (min 4 chars).",
    ),
) -> None:
    """Pretty-print one session — the newest by default, or one by uuid prefix."""
    logs_dir = default_logs_dir()
    try:
        path = resolve_session(logs_dir, session)
    except FileNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    events = load_session(path)
    if last is not None and last >= 0:
        events = events[-last:] if last else []

    console = Console()
    session_id = session_id_from_path(path)
    table = Table(title=f"Session {session_id} ({path.name})")
    # "time" is shown as an absolute HH:MM:SS.mmm (UTC) — absolute means
    # a log slice is still interpretable when the reader doesn't know
    # which row was the first event of the session. If this ever needs
    # to be relative, it's a one-line swap in _format_time_absolute.
    table.add_column("time", style="dim", no_wrap=True)
    table.add_column("event_type", style="magenta", no_wrap=True)
    table.add_column("summary")
    for event in events:
        table.add_row(
            _format_time_absolute(event),
            event.event_type,
            _summarize_event(event),
        )
    console.print(table)


@app.command("export")
def export_session(
    output: Path = typer.Option(..., "--output", help="Destination .jsonl path."),  # noqa: B008
    session: str | None = typer.Option(
        None,
        "--session",
        help="Export a specific session by uuid prefix (min 4 chars).",
    ),
) -> None:
    """Copy a session log to ``--output`` verbatim (no transformation)."""
    logs_dir = default_logs_dir()
    try:
        path = resolve_session(logs_dir, session)
    except (FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc

    if output.exists():
        typer.echo(
            f"Refusing to overwrite existing file: {output}. "
            "Pick another --output path or remove the existing file first."
        )
        raise typer.Exit(code=1)

    # Byte-for-byte copy: the file is already redacted at write time, so
    # re-serializing through Event would only introduce formatting drift
    # without adding value. shutil.copy preserves mtime which helps the
    # user correlate an exported log with the session it came from.
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, output)

    count = len(load_session(output))
    typer.echo(f"exported {count} events to {output}")


__all__ = ["app"]
