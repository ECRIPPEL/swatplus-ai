"""Pure adapters between domain objects and :mod:`swatplus_ai.api.models`.

These functions take a parsed :class:`~swatplus_ai.parser.txtinout.TxtInOutProject`
or a :class:`~swatplus_ai.diagnostics.finding.Finding` and produce the
corresponding view-model. They never call the network, the parser, or the
rule engine themselves — that wiring lives in the FastAPI layer in
slice 3.3. Keeping the mapping logic in pure functions means tests can
assert the shape and values with a single parsed fixture, no server.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date, timedelta

from swatplus_ai.api.models import Citation, FindingVM, LanduseSlice, ProjectMeta
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.parser.txtinout import TxtInOutProject

_UNKNOWN = ""


def _julian_to_iso(year: int, day_of_year: int) -> str:
    """Convert a (calendar year, Julian day) pair into an ISO date string.

    SWAT+ ``time.sim`` and ``print.prt`` both record simulation bounds as
    (day_of_year, year). Clamp the day into ``[1, 366]`` defensively —
    the parser already validates the range, but an out-of-band value
    would surface as a crash here, which is worse than a slightly-off
    date label.
    """
    day = max(1, min(366, day_of_year))
    return (date(year, 1, 1) + timedelta(days=day - 1)).isoformat()


def _sum_hru_area_km2(project: TxtInOutProject) -> float:
    """Sum ``hru.con`` area across every HRU.

    ``hru.con`` stores area in hectares (SWAT+ convention); we report
    the basin area in km² to match the UI label. Returns ``0.0`` when
    the project ships without ``hru.con`` — a trimmed-down sketch
    legitimately has no HRU graph.
    """
    if project.hru_con is None:
        return 0.0
    hectares = sum(row.area for row in project.hru_con.rows)
    return round(hectares / 100.0, 2)


def _outfall_lat_lon(project: TxtInOutProject, outfall_name: str) -> tuple[float, float]:
    """Return ``(lat, lon)`` of the outfall channel, or ``(0.0, 0.0)`` if absent."""
    if project.chandeg_con is None or not outfall_name:
        return (0.0, 0.0)
    row = project.chandeg_con.by_name(outfall_name)
    if row is None:
        return (0.0, 0.0)
    return (row.lat, row.lon)


def to_project_meta(
    project: TxtInOutProject,
    *,
    ready_to_run: bool,
) -> ProjectMeta:
    """Build a :class:`ProjectMeta` from a parsed project.

    ``ready_to_run`` is caller-supplied rather than computed here because
    it depends on diagnostic findings — callers that have already run the
    engine pass the real flag; tests that just want a metadata snapshot
    can pass ``False`` without re-running rules.

    Fields the parser doesn't currently populate (``climate``, ``biome``,
    ``model_version``) land as empty strings rather than ``None`` so the
    TypeScript surface stays free of null checks.
    """
    folder = project.folder
    time_sim = project.time_sim
    print_prt = project.print_prt
    obj = project.object_cnt
    outfalls = project.topology.outfall_channels()
    outfall_name = outfalls[0] if outfalls else _UNKNOWN
    lat, lon = _outfall_lat_lon(project, outfall_name)

    return ProjectMeta(
        name=folder.name,
        path=str(folder),
        simulation_start=_julian_to_iso(time_sim.yrc_start, time_sim.day_start),
        simulation_end=_julian_to_iso(time_sim.yrc_end, time_sim.day_end),
        warmup_years=print_prt.nyskip,
        subbasins=obj.rtu if obj is not None else 0,
        hrus=obj.hru if obj is not None else 0,
        channels=obj.cha if obj is not None else 0,
        weather_stations=len(project.weather_sta.rows),
        model_version=_UNKNOWN,
        outfall_channel=outfall_name,
        climate=_UNKNOWN,
        area_km2=_sum_hru_area_km2(project),
        ready_to_run=ready_to_run,
        outlet_lat=lat,
        outlet_lon=lon,
        biome=_UNKNOWN,
    )


def _format_evidence(evidence: dict[str, object]) -> str:
    """Render the evidence dict as a stable, human-readable string.

    The UI renders this inside a ``<pre>`` block, so a JSON dump with a
    2-space indent reads better than Python's ``repr``. Sort keys so
    snapshot tests don't break when Python dict ordering shifts.
    """
    return json.dumps(evidence, indent=2, sort_keys=True, default=str)


def _references_to_citations(refs: Iterable[str]) -> tuple[Citation, ...]:
    """Wrap reference keys in placeholder :class:`Citation` records.

    Rules today emit reference *keys* (``"plunge_2024"``, ``"moriasi_2007"``)
    without an accompanying label/source triple. Until the citation
    registry lands, each ref becomes a :class:`Citation` whose three
    fields all hold the same key — the UI still renders clickable
    superscripts and the drift will be obvious when a proper registry
    arrives.
    """
    return tuple(Citation(id=ref, label=ref, source=ref) for ref in refs)


def to_finding_vm(finding: Finding) -> FindingVM:
    """Convert a domain :class:`Finding` into a UI :class:`FindingVM`.

    Two asymmetries worth knowing:

    * The domain ``message`` is rendered as the UI ``title`` — rules
      today produce a single-line summary that maps cleanly to the
      4-panel UI's top row. ``explanation`` and ``suggestion`` stay
      empty because the current rule YAML doesn't carry those fields.
    * ``references`` (tuple of opaque keys) becomes ``citations``
      (list of placeholder :class:`Citation` records); see
      :func:`_references_to_citations` for the temporary shape.
    """
    return FindingVM(
        id=finding.id,
        rule_id=finding.rule_ref,
        severity=finding.severity,
        title=finding.message,
        location=finding.location or _UNKNOWN,
        evidence=_format_evidence(finding.evidence),
        explanation=_UNKNOWN,
        suggestion=_UNKNOWN,
        citations=_references_to_citations(finding.references),
    )


def to_landuse_slices(project: TxtInOutProject) -> tuple[LanduseSlice, ...]:
    """Aggregate HRU areas by land-use class for the Home donut chart.

    Joins :class:`hru_data` rows to :class:`hru_con` (for area) via the
    shared HRU ``name``, then groups by the ``lu_mgt`` reference (the
    land-use class name, e.g. ``agrl_lum``, ``frst_lum``). Returns an
    empty tuple when either file is missing — the UI can render a
    "no landuse" placeholder instead of crashing.

    Order is deterministic: slices are sorted by descending ``pct`` so
    the donut always opens on the dominant class.
    """
    if project.hru_con is None:
        return ()

    area_by_lu_mgt: dict[str, float] = {}
    total_ha = 0.0
    for hru_data_row in project.hru_data.rows:
        lu_mgt = hru_data_row.lu_mgt
        if lu_mgt is None:
            continue
        con_row = project.hru_con.by_name(hru_data_row.name)
        if con_row is None:
            continue
        area_by_lu_mgt[lu_mgt] = area_by_lu_mgt.get(lu_mgt, 0.0) + con_row.area
        total_ha += con_row.area

    if total_ha <= 0.0:
        return ()

    slices = [
        LanduseSlice(
            class_name=lu_mgt,
            name=lu_mgt,
            pct=round(area_ha / total_ha * 100.0, 2),
            area_km2=round(area_ha / 100.0, 2),
        )
        for lu_mgt, area_ha in area_by_lu_mgt.items()
    ]
    slices.sort(key=lambda s: s.pct, reverse=True)
    return tuple(slices)


__all__ = [
    "to_finding_vm",
    "to_landuse_slices",
    "to_project_meta",
]
