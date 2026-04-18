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

from swatplus_ai.diagnostics.engine import DiagnosticEngine
from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.diagnostics.registry import CheckResult, register_check
from swatplus_ai.diagnostics.rule import Rule

__all__ = [
    "CheckResult",
    "DiagnosticEngine",
    "Finding",
    "Rule",
    "register_check",
]
