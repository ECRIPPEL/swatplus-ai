"""Module 1 prompt assembler.

Pure functions that turn a set of deterministic :class:`Finding` objects,
a :class:`ProjectSummary`, and zero-or-more :class:`StaticPassage`
snippets into a two-message conversation (``system`` + ``user``) suitable
for any backend that speaks the
:class:`swatplus_ai.llm.interface.Message` contract.

The system prompt body lives in ``module1_system.md`` next to this
module. It is versioned data, not code — edit the markdown to change
tone or add ground rules; edit this file only to change the *shape* of
the rendering (what blocks exist, in what order, with what placeholders).
"""

from __future__ import annotations

from collections.abc import Sequence
from importlib.resources import files

from pydantic import BaseModel, ConfigDict

from swatplus_ai.diagnostics.finding import Finding, Severity
from swatplus_ai.llm.interface import Message
from swatplus_ai.parser.txtinout import TxtInOutProject

_TEMPLATE_RESOURCE = "module1_system.md"

_SEVERITY_ORDER: tuple[Severity, ...] = ("error", "warning", "info")

_USER_OPENING = (
    "Based on the structured findings and project summary above, please "
    "provide a diagnostic report: (1) summarize the project, (2) list "
    "errors with suggested fixes, (3) list warnings with context, "
    "(4) note any setup concerns not captured by the rules."
)


class ProjectSummary(BaseModel):
    """Condensed, LLM-friendly view of a parsed SWAT+ project.

    The full :class:`TxtInOutProject` carries hundreds of fields across
    dozens of nested pydantic models; dropping the whole thing into a
    prompt would blow through context windows and bury the signal. This
    summary keeps only the headline numbers the LLM actually needs to
    orient itself — the same numbers a modeler would read off QSWAT+
    before opening the TxtInOut folder.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sim_start_year: int | None = None
    sim_end_year: int | None = None
    warmup_years: int | None = None
    n_hrus: int | None = None
    n_channels: int | None = None
    n_aquifers: int | None = None
    n_subbasins: int | None = None
    pet_method: int | None = None
    basin_area_km2: float | None = None

    @classmethod
    def from_project(cls, project: TxtInOutProject) -> ProjectSummary:
        """Build a summary from a parsed :class:`TxtInOutProject`.

        ``object.cnt`` is optional on the project (a trimmed fixture
        may ship without it), so every count field gracefully degrades
        to ``None`` when it is absent rather than raising.
        """
        obj = project.object_cnt
        return cls(
            sim_start_year=project.time_sim.yrc_start,
            sim_end_year=project.time_sim.yrc_end,
            warmup_years=project.print_prt.nyskip,
            n_hrus=obj.hru if obj is not None else None,
            n_channels=obj.cha if obj is not None else None,
            n_aquifers=obj.aqu if obj is not None else None,
            n_subbasins=obj.rtu if obj is not None else None,
            pet_method=project.codes_bsn.pet,
            basin_area_km2=obj.tot_area if obj is not None else None,
        )


class StaticPassage(BaseModel):
    """One static documentation snippet handed to the prompt builder.

    Until a real retrieval layer lands (Phase 2), callers inline
    passages by hand. Slice 6.1 defines the contract only; no retrieval
    logic is implemented here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    body: str
    source: str


def _load_template() -> str:
    """Read the markdown template shipped alongside this module."""
    return files("swatplus_ai.prompts").joinpath(_TEMPLATE_RESOURCE).read_text(encoding="utf-8")


def _render_project_summary(summary: ProjectSummary) -> str:
    lines = []
    for field, value in summary.model_dump().items():
        pretty = "—" if value is None else str(value)
        lines.append(f"- {field}: {pretty}")
    return "\n".join(lines)


def _render_findings(findings: Sequence[Finding]) -> str:
    if not findings:
        return "No findings emitted by the rule engine."
    groups: dict[Severity, list[Finding]] = {sev: [] for sev in _SEVERITY_ORDER}
    for f in findings:
        groups[f.severity].append(f)
    blocks: list[str] = []
    for sev in _SEVERITY_ORDER:
        for f in sorted(groups[sev], key=lambda finding: finding.id):
            refs = ", ".join(f.references) if f.references else "—"
            loc = f.location if f.location is not None else "—"
            blocks.append(
                f"### {sev}: {f.id}\n"
                f"- location: {loc}\n"
                f"- message: {f.message}\n"
                f"- references: {refs}"
            )
    return "\n\n".join(blocks)


def _render_static_passages(passages: Sequence[StaticPassage] | None) -> str:
    if not passages:
        return "None provided."
    blocks: list[str] = []
    for p in passages:
        blocks.append(f"## [{p.id}] {p.title}\n{p.body}\nsource: {p.source}")
    return "\n\n".join(blocks)


def build_module1_prompt(
    findings: Sequence[Finding],
    project_summary: ProjectSummary,
    static_passages: Sequence[StaticPassage] | None = None,
) -> list[Message]:
    """Build the full Module 1 prompt as a 2-message conversation.

    Returns ``[Message(role="system", content=<rendered template>),
    Message(role="user", content=<opening question>)]``. The caller
    is responsible for dispatching the list to an
    :class:`~swatplus_ai.llm.interface.LLMBackend`.
    """
    template = _load_template()
    system = (
        template.replace("{{PROJECT_SUMMARY}}", _render_project_summary(project_summary))
        .replace("{{FINDINGS}}", _render_findings(findings))
        .replace("{{STATIC_PASSAGES}}", _render_static_passages(static_passages))
    )
    return [
        Message(role="system", content=system),
        Message(role="user", content=_USER_OPENING),
    ]


__all__ = ["ProjectSummary", "StaticPassage", "build_module1_prompt"]
