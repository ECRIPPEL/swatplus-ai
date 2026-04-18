"""Deterministic rule engine for SWAT+ project diagnostics.

:class:`DiagnosticEngine` glues the declarative half (YAML-loaded
:class:`~swatplus_ai.diagnostics.rule.Rule` objects) to the imperative
half (Python check functions registered in
:mod:`swatplus_ai.diagnostics.registry`). Callers hand it a parsed
:class:`~swatplus_ai.parser.txtinout.TxtInOutProject` and a pipeline
stage (``"setup"``, ``"calibration"``, ``"evaluation"``) — the engine
filters rules by stage, skips any whose ``requires`` attrs are missing
on the project (so rules keyed on output files are no-ops until a
simulation has been run), runs each check function, and wraps each
:class:`~swatplus_ai.diagnostics.registry.CheckResult` into a
:class:`~swatplus_ai.diagnostics.finding.Finding`.

``requires`` names resolve against both top-level project fields
(``time_sim``, ``print_prt`` …) and fields on the nested
``project.outputs`` namespace (``basin_wb_aa``, ``channel_sd_aa`` …),
so YAML authors can use either flat or nested names without worrying
which namespace a parser landed in. Dotted forms (``outputs.basin_wb_aa``)
are also accepted and walked attribute-by-attribute, so rules that want
to be explicit about where a dependency lives can be.

**Fail-loud at construction:** if any rule references a check name that
isn't in the registry, or any rule id is duplicated across files,
:meth:`DiagnosticEngine.from_directory` /
:meth:`DiagnosticEngine.from_builtin_rules` raise immediately —
misconfiguration never silently produces an empty report.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.diagnostics.registry import CheckResult, get_check
from swatplus_ai.diagnostics.rule import Rule

if TYPE_CHECKING:
    from swatplus_ai.parser.txtinout import TxtInOutProject

_MISSING = object()


def _builtin_rules_dir() -> Path:
    """Locate the ``rules/`` directory shipped with the installed package."""
    return Path(__file__).resolve().parent / "rules"


def _unsatisfied(project: TxtInOutProject, attr: str) -> bool:
    """Return True when ``attr`` is absent or ``None`` on the project.

    Three resolution paths, tried in order: a dotted path walked
    attribute-by-attribute (``outputs.basin_wb_aa``); a top-level
    project field (``time_sim``); and — as a convenience so YAML can
    stay flat — the nested ``project.outputs`` namespace
    (``basin_wb_aa``). Using identity checks (``is None`` /
    ``is _MISSING``) rather than ``value in (None, ...)`` matters
    because some fields hold :class:`pandas.DataFrame`, whose
    ``__eq__`` would raise on a value-membership test.
    """
    if "." in attr:
        value: object = project
        for part in attr.split("."):
            value = getattr(value, part, _MISSING)
            if value is _MISSING or value is None:
                return True
        return False

    value = getattr(project, attr, _MISSING)
    if value is _MISSING:
        outputs = getattr(project, "outputs", None)
        if outputs is not None:
            value = getattr(outputs, attr, _MISSING)
    return value is None or value is _MISSING


def _to_finding(rule: Rule, result: CheckResult) -> Finding:
    message = rule.message.format_map(result.evidence)
    return Finding(
        id=rule.id,
        severity=result.severity if result.severity is not None else rule.severity,
        location=result.location,
        evidence=result.evidence,
        rule_ref=rule.id,
        message=message,
        references=rule.references,
    )


class DiagnosticEngine:
    """Runs a fixed set of rules against parsed SWAT+ projects."""

    def __init__(self, rules: tuple[Rule, ...]) -> None:
        seen: set[str] = set()
        for rule in rules:
            if rule.id in seen:
                raise ValueError(f"Duplicate rule id: {rule.id!r}")
            seen.add(rule.id)
            # Fail loud now if the check name isn't registered.
            get_check(rule.check)
        self._rules = rules

    @property
    def rules(self) -> tuple[Rule, ...]:
        return self._rules

    @classmethod
    def from_directory(cls, path: Path) -> DiagnosticEngine:
        """Load every ``*.yaml`` directly under ``path`` as a rule."""
        path = Path(path)
        if not path.is_dir():
            raise NotADirectoryError(f"Rule directory not found: {path}")
        loaded = [Rule.load(p) for p in sorted(path.glob("*.yaml"))]
        return cls(tuple(loaded))

    @classmethod
    def from_builtin_rules(cls) -> DiagnosticEngine:
        """Load rules shipped inside the installed package."""
        rules_dir = _builtin_rules_dir()
        if not rules_dir.is_dir():
            return cls(())
        loaded = [Rule.load(p) for p in sorted(rules_dir.glob("*.yaml"))]
        return cls(tuple(loaded))

    def run(self, project: TxtInOutProject, *, stage: str = "setup") -> list[Finding]:
        """Run every rule matching ``stage`` and collect their findings."""
        findings: list[Finding] = []
        for rule in self._rules:
            if stage not in rule.stage:
                continue
            if any(_unsatisfied(project, attr) for attr in rule.requires):
                continue
            fn = get_check(rule.check)
            result = fn(project)
            if result is None:
                continue
            if isinstance(result, CheckResult):
                findings.append(_to_finding(rule, result))
            else:
                findings.extend(_to_finding(rule, r) for r in result)
        return findings


__all__ = ["DiagnosticEngine"]
