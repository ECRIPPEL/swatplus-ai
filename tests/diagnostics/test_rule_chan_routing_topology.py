"""Tests for rule ``chan.routing_topology``."""

from __future__ import annotations

from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.inputs.chandeg_con import ChandegConRow
from swatplus_ai.parser.models import ConConnection
from swatplus_ai.parser.txtinout import TxtInOutProject


def _engine() -> DiagnosticEngine:
    return DiagnosticEngine.from_builtin_rules()


def _findings(project: TxtInOutProject) -> list[Finding]:
    return [f for f in _engine().run(project, stage="setup") if f.id == "chan.routing_topology"]


def _row(
    *,
    id: int,
    name: str,
    out_tot: int,
    connections: tuple[ConConnection, ...],
    base: ChandegConRow,
) -> ChandegConRow:
    """Clone ``base`` while swapping the topology-relevant fields."""
    return base.model_copy(
        update={"id": id, "name": name, "out_tot": out_tot, "connections": connections},
    )


def test_routing_topology_clean_project(clean_setup_project: TxtInOutProject) -> None:
    # clean_setup_project already rewrites the sole row into an outfall.
    assert _findings(clean_setup_project) == []


def test_routing_topology_no_outfall(clean_setup_project: TxtInOutProject) -> None:
    assert clean_setup_project.chandeg_con is not None
    base = clean_setup_project.chandeg_con.rows[0]
    r1 = _row(
        id=1,
        name="cha001",
        out_tot=1,
        connections=(ConConnection(obj_typ="sdc", obj_id=2, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    r2 = _row(
        id=2,
        name="cha002",
        out_tot=1,
        connections=(ConConnection(obj_typ="sdc", obj_id=1, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    chandeg = clean_setup_project.chandeg_con.model_copy(update={"rows": (r1, r2)})
    project = clean_setup_project.model_copy(update={"chandeg_con": chandeg})
    findings = _findings(project)
    reasons = [f.evidence["reason"] for f in findings]
    # Both the outfall-missing finding and the cycle are expected.
    assert any("no outfall" in r for r in reasons)
    assert any("cycle detected" in r for r in reasons)


def test_routing_topology_out_tot_mismatch(clean_setup_project: TxtInOutProject) -> None:
    assert clean_setup_project.chandeg_con is not None
    base = clean_setup_project.chandeg_con.rows[0]
    # out_tot says 2 but only one connection present — and to keep an outfall
    # in the graph, append a second row with no channel edges.
    r1 = _row(
        id=1,
        name="cha001",
        out_tot=2,
        connections=(ConConnection(obj_typ="sdc", obj_id=2, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    r2 = _row(id=2, name="cha002", out_tot=0, connections=(), base=base)
    chandeg = clean_setup_project.chandeg_con.model_copy(update={"rows": (r1, r2)})
    project = clean_setup_project.model_copy(update={"chandeg_con": chandeg})
    findings = _findings(project)
    mismatches = [f for f in findings if "out_tot" in f.evidence.get("reason", "")]
    assert len(mismatches) == 1
    f = mismatches[0]
    assert f.severity == "error"
    assert f.evidence["declared"] == 2
    assert f.evidence["actual"] == 1


def test_routing_topology_frac_sum_off(clean_setup_project: TxtInOutProject) -> None:
    assert clean_setup_project.chandeg_con is not None
    base = clean_setup_project.chandeg_con.rows[0]
    r1 = _row(
        id=1,
        name="cha001",
        out_tot=2,
        connections=(
            ConConnection(obj_typ="sdc", obj_id=2, hyd_typ="tot", frac=0.4),
            ConConnection(obj_typ="sdc", obj_id=2, hyd_typ="tot", frac=0.4),
        ),
        base=base,
    )
    r2 = _row(id=2, name="cha002", out_tot=0, connections=(), base=base)
    chandeg = clean_setup_project.chandeg_con.model_copy(update={"rows": (r1, r2)})
    project = clean_setup_project.model_copy(update={"chandeg_con": chandeg})
    findings = _findings(project)
    frac = [f for f in findings if "fractions sum" in f.evidence.get("reason", "")]
    assert len(frac) == 1
    # Per-result severity override on the CheckResult wins over the rule's error severity.
    assert frac[0].severity == "warning"
    assert frac[0].evidence["frac_sum"] == 0.8


def test_routing_topology_downstream_out_of_range(clean_setup_project: TxtInOutProject) -> None:
    assert clean_setup_project.chandeg_con is not None
    base = clean_setup_project.chandeg_con.rows[0]
    r1 = _row(
        id=1,
        name="cha001",
        out_tot=1,
        connections=(ConConnection(obj_typ="sdc", obj_id=99, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    r2 = _row(id=2, name="cha002", out_tot=0, connections=(), base=base)
    chandeg = clean_setup_project.chandeg_con.model_copy(update={"rows": (r1, r2)})
    project = clean_setup_project.model_copy(update={"chandeg_con": chandeg})
    findings = _findings(project)
    out_of_range = [f for f in findings if "out of range" in f.evidence.get("reason", "")]
    assert len(out_of_range) == 1
    assert out_of_range[0].evidence["obj_id"] == 99


def test_routing_topology_cycle(clean_setup_project: TxtInOutProject) -> None:
    # Three-channel cycle cha001 -> cha002 -> cha003 -> cha001, plus
    # a separate outfall cha004 so the outfall check stays silent.
    assert clean_setup_project.chandeg_con is not None
    base = clean_setup_project.chandeg_con.rows[0]
    r1 = _row(
        id=1,
        name="cha001",
        out_tot=1,
        connections=(ConConnection(obj_typ="sdc", obj_id=2, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    r2 = _row(
        id=2,
        name="cha002",
        out_tot=1,
        connections=(ConConnection(obj_typ="sdc", obj_id=3, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    r3 = _row(
        id=3,
        name="cha003",
        out_tot=1,
        connections=(ConConnection(obj_typ="sdc", obj_id=1, hyd_typ="tot", frac=1.0),),
        base=base,
    )
    r4 = _row(id=4, name="cha004", out_tot=0, connections=(), base=base)
    chandeg = clean_setup_project.chandeg_con.model_copy(update={"rows": (r1, r2, r3, r4)})
    project = clean_setup_project.model_copy(update={"chandeg_con": chandeg})
    findings = _findings(project)
    cycles = [f for f in findings if "cycle detected" in f.evidence.get("reason", "")]
    assert len(cycles) == 1
    assert cycles[0].evidence["cycle"] == "cha001 -> cha002 -> cha003 -> cha001"
