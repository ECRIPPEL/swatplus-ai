"""Deterministic rule engine for SWAT+ project diagnostics.

Public surface:

* :class:`DiagnosticEngine` — loads YAML rules and runs them against a
  parsed :class:`~swatplus_ai.parser.txtinout.TxtInOutProject`.
* :class:`Finding` — one structured observation emitted by the engine.
* :class:`Rule` — declarative metadata backing a single diagnostic check.
* :class:`CheckResult` — raw output of a check function before the engine
  wraps it into a :class:`Finding`.
* :func:`register_check` — decorator that binds a Python function to the
  name a YAML rule references via its ``check:`` field.
"""

from __future__ import annotations

# Side-effect import: loading the ``checks`` subpackage runs every
# ``@register_check(...)`` decorator that backs a bundled YAML rule, so
# ``DiagnosticEngine.from_builtin_rules()`` finds its check functions
# without callers having to remember to import them.
from swatplus_ai.diagnostics import checks as _checks  # noqa: F401
from swatplus_ai.diagnostics.drift import (
    DriftCategory,
    DriftRecord,
    DriftRegistry,
    current_registry,
    record_drift,
)
from swatplus_ai.diagnostics.engine import DiagnosticEngine
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.diagnostics.registry import CheckResult, register_check
from swatplus_ai.diagnostics.rule import Rule

__all__ = [
    "CheckResult",
    "DiagnosticEngine",
    "DriftCategory",
    "DriftRecord",
    "DriftRegistry",
    "Finding",
    "Rule",
    "current_registry",
    "record_drift",
    "register_check",
]
