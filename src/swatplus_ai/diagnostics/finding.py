"""Structured findings emitted by the diagnostic rule engine.

A ``Finding`` is the deterministic output of one rule executing against a
parsed :class:`~swatplus_ai.parser.txtinout.TxtInOutProject`. The LLM-facing
layers (prompt assembler, Module 1 report renderer) consume these — they
are the contract between the rule engine and everything downstream. The
message field is already rendered (template substituted from evidence) so
consumers don't re-run the template and risk drifting from the original
rule text.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["info", "warning", "error"]


class Finding(BaseModel):
    """One diagnostic observation about a SWAT+ project."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    severity: Severity
    location: str | None
    evidence: dict[str, Any]
    rule_ref: str
    message: str
    references: tuple[str, ...] = ()


__all__ = ["Finding", "Severity"]
