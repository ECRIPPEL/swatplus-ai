"""End-to-end orchestrator for ``swatplus-ai check <path>`` (Module 1).

Three concerns, one module:

1. :func:`run_setup_check` — parses the TxtInOut project, runs the setup
   stage of the diagnostic engine, builds the Module-1 prompt, dispatches
   one :meth:`LLMBackend.complete` call, and parses the reply through
   :func:`format_module1_response`. Telemetry (``session_start`` /
   ``session_end`` / ``user_action``) is the CLI's job — this function
   stays pure so tests and future callers (e.g. a web UI) can consume it
   without inheriting the CLI's side effects.
2. :class:`SetupCheckResult` — the frozen bundle every caller receives.
   Carries the project path, the condensed :class:`ProjectSummary`, the
   deterministic findings, the parsed LLM response (``None`` when
   ``skip_llm=True``), and the wall-clock of the whole orchestration.
3. :func:`render_setup_check_result` — the Rich renderer. Kept in the
   same file as the orchestrator because the two evolve together; when
   we add a field to the result we almost always add a row or panel
   here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.llm.interface import LLMBackend
from swatplus_ai.parser.txtinout import TxtInOutProject
from swatplus_ai.prompts import (
    FormattedResponse,
    ProjectSummary,
    build_module1_prompt,
    collect_handles,
    format_module1_response,
)

_SEVERITY_STYLE = {
    "error": "bold red",
    "warning": "yellow",
    "info": "cyan",
}


@dataclass(frozen=True)
class SetupCheckResult:
    """Frozen bundle returned by :func:`run_setup_check`."""

    project_path: Path
    summary: ProjectSummary
    findings: tuple[Finding, ...]
    response: FormattedResponse | None
    duration_ms: int


async def run_setup_check(
    path: Path,
    *,
    backend: LLMBackend,
    skip_llm: bool = False,
    stage: str = "setup",
) -> SetupCheckResult:
    """Parse ``path``, run setup rules, and optionally call the LLM.

    Parameters
    ----------
    path:
        Directory containing a SWAT+ ``TxtInOut`` project.
    backend:
        Backend used when ``skip_llm`` is ``False``. Unused otherwise —
        callers that know they only want the rule-engine output can
        still pass a :class:`~swatplus_ai.llm.backends.mock.MockBackend`
        or any sentinel that satisfies the protocol.
    skip_llm:
        When ``True``, return ``response=None`` without dispatching a
        completion. Useful for offline runs and for tests that don't
        want to script a reply.
    stage:
        Diagnostic pipeline stage. Defaults to ``"setup"`` because that
        is the only stage wired into Module 1 today; the kwarg is kept
        so Module 2/3 can reuse the orchestrator without a fork.
    """
    t0 = time.perf_counter()
    project = TxtInOutProject.read(path)
    engine = DiagnosticEngine.from_builtin_rules()
    findings = tuple(engine.run(project, stage=stage))
    summary = ProjectSummary.from_project(project)

    response: FormattedResponse | None = None
    if not skip_llm:
        messages = build_module1_prompt(list(findings), summary)
        llm_response = await backend.complete(messages)
        known = collect_handles(findings)
        response = format_module1_response(llm_response.text, known)

    duration_ms = round((time.perf_counter() - t0) * 1000)
    return SetupCheckResult(
        project_path=Path(path),
        summary=summary,
        findings=findings,
        response=response,
        duration_ms=duration_ms,
    )


def _render_summary_panel(summary: ProjectSummary, project_path: Path) -> Panel:
    body = Table.grid(padding=(0, 2))
    body.add_column(style="bold")
    body.add_column()
    for field, value in summary.model_dump().items():
        body.add_row(field, "—" if value is None else str(value))
    return Panel(body, title=f"Project summary — {project_path}", border_style="cyan")


def _render_findings_table(findings: tuple[Finding, ...]) -> Table:
    table = Table(
        title=f"Diagnostic findings ({len(findings)})",
        show_lines=False,
        expand=True,
    )
    table.add_column("severity", no_wrap=True)
    table.add_column("rule", style="magenta", no_wrap=True)
    table.add_column("location", style="dim")
    table.add_column("message")
    for finding in findings:
        style = _SEVERITY_STYLE.get(finding.severity, "")
        table.add_row(
            Text(finding.severity, style=style),
            finding.id,
            finding.location or "—",
            finding.message,
        )
    return table


def _render_response_panel(response: FormattedResponse) -> Panel:
    body = Text(response.text)
    # Highlight every citation span so the reader sees which handles the
    # LLM actually pinned. We colour known vs. unknown differently so a
    # skim catches citations that point outside the allowlist.
    unknown = set(response.unknown_citations)
    for citation in response.citations:
        style = "red" if citation.handle in unknown else "green"
        body.stylize(style, citation.start, citation.end)

    title = "LLM response"
    if response.has_unknown_citations:
        title += f" — unknown handles: {', '.join(response.unknown_citations)}"
    return Panel(body, title=title, border_style="green")


def render_setup_check_result(result: SetupCheckResult, console: Console) -> None:
    """Print ``result`` to ``console`` in a three-section Rich layout.

    Layout: (1) project-summary panel, (2) findings table, (3) LLM
    response panel — with citations highlighted and unknown handles
    called out in the title. The LLM panel is omitted when
    ``result.response is None`` (offline / ``--skip-llm`` runs) so the
    output stays honest about what ran.
    """
    console.print(_render_summary_panel(result.summary, result.project_path))
    console.print(_render_findings_table(result.findings))
    if result.response is not None:
        console.print(_render_response_panel(result.response))
    console.print(f"[dim]completed in {result.duration_ms} ms[/dim]")


__all__ = [
    "SetupCheckResult",
    "render_setup_check_result",
    "run_setup_check",
]
