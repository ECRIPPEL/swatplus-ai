"""UI-facing Pydantic view-models for the ``swatplus-ai serve`` HTTP API.

Every class here is deliberately named after its TypeScript counterpart in
``ui/src/lib/schemas.ts`` (``ProjectMeta`` → ``ProjectMeta`` interface,
``FindingVM`` → ``FindingVM`` interface, etc.). Names never collide with
domain classes elsewhere in ``swatplus_ai`` — a reader seeing ``FindingVM``
knows immediately it belongs to the API layer, not the diagnostic engine's
:class:`~swatplus_ai.diagnostics.finding.Finding`.

All models emit JSON with ``camelCase`` keys (via ``alias_generator``) so
the TS types feel native on the UI side. ``populate_by_name=True`` keeps
server-side Python happy writing snake_case field names in kwargs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Severity = Literal["info", "warning", "error"]


def _vm_config() -> ConfigDict:
    return ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
        extra="forbid",
    )


class Citation(BaseModel):
    """One citation attached to a finding or LLM response."""

    model_config = _vm_config()

    id: str
    label: str
    source: str


class FindingVM(BaseModel):
    """UI-shaped view of a :class:`~swatplus_ai.diagnostics.finding.Finding`.

    The domain ``Finding`` stores a rendered ``message`` plus raw evidence
    (``dict``) and a rule-ref string; the UI wants a 4-panel layout (title
    / evidence / explanation / suggestion) plus Citation records. The
    adapter fills what the current domain has and leaves ``explanation``
    and ``suggestion`` empty when the rule set doesn't provide them —
    that gap is intentional and will close as rules grow richer.
    """

    model_config = _vm_config()

    id: str
    rule_id: str
    severity: Severity
    title: str
    location: str
    evidence: str
    explanation: str
    suggestion: str
    citations: tuple[Citation, ...]


class ProjectMeta(BaseModel):
    """Landing-page snapshot of a parsed SWAT+ project.

    Supersets :class:`~swatplus_ai.prompts.builder.ProjectSummary` with the
    fields the UI Home screen asks for (outlet lat/lon, biome, ready-to-run
    flag, etc.). Fields the current parser can't populate yet are typed as
    ``str`` / ``float`` with empty-string or ``0.0`` defaults rather than
    ``Optional`` so the TS surface stays simple — the UI can render ``""``
    as "unknown" without adding null checks to every label.
    """

    model_config = _vm_config()

    name: str
    path: str
    simulation_start: str
    simulation_end: str
    warmup_years: int
    subbasins: int
    hrus: int
    channels: int
    weather_stations: int
    model_version: str
    outfall_channel: str
    climate: str
    area_km2: float
    ready_to_run: bool
    outlet_lat: float
    outlet_lon: float
    biome: str


class LanduseSlice(BaseModel):
    """One class row in the Home landuse donut chart."""

    model_config = _vm_config()

    class_name: str
    name: str
    pct: float
    area_km2: float


__all__ = [
    "Citation",
    "FindingVM",
    "LanduseSlice",
    "ProjectMeta",
    "Severity",
]
