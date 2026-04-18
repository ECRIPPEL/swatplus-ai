"""YAML-loaded rule metadata for the diagnostic engine.

A :class:`Rule` is the declarative half of a diagnostic check. The
imperative half — the actual computation that inspects the parsed
project — lives as a Python function registered under ``Rule.check`` in
the check registry. Keeping the two apart means contributors can drop a
YAML file to add severity / stage / message metadata for an existing
check, without touching Python; it also means the engine can validate
rule structure (fields, stages, severity levels) up-front via pydantic.

The architecture doc sketches an inline YAML DSL (``check: et / precip
not in [0.55, 0.90]``). That is deliberately replaced by a
function-name-in-registry lookup here, because real rules (FK
consistency, cycle detection, weather-gap analysis) cannot be expressed
as one-line expressions without inventing a half-baked language. If a
rule wants data-driven thresholds, add a ``params`` field and pass it to
the check function — do not invent an expression parser.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from swatplus_ai.diagnostics.finding import Severity

Stage = Literal["setup", "calibration", "evaluation"]


class Rule(BaseModel):
    """Declarative metadata for one diagnostic rule."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    severity: Severity
    stage: tuple[Stage, ...] = Field(min_length=1)
    requires: tuple[str, ...] = ()
    check: str
    message: str
    references: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path) -> Rule:
        """Parse ``path`` as a single-rule YAML document."""
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"Rule file must contain a mapping: {path}")
        return cls.model_validate(raw)


__all__ = ["Rule", "Stage"]
