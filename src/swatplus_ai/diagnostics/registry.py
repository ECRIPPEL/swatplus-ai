"""Check-function registry for the diagnostic engine.

Each diagnostic rule's imperative half is a plain Python function that
inspects a parsed :class:`~swatplus_ai.parser.txtinout.TxtInOutProject`
and returns zero, one, or many :class:`CheckResult` objects — the engine
pairs each result with the rule's declarative metadata (severity, id,
message template, references) to produce a :class:`Finding`.

Registering by name (decorator) instead of by import path keeps YAML
rule files terse (``check: setup.files_present`` rather than a dotted
``swatplus_ai.diagnostics.checks.setup:files_present``) and gives the
engine one lookup point where it can fail loudly at construction time
if a rule references a name nobody registered.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from swatplus_ai.parser.txtinout import TxtInOutProject


class CheckResult(BaseModel):
    """One raw observation produced by a check function.

    The engine converts this into a :class:`Finding` by copying the
    rule's id / severity / message / references onto it. ``location``
    is a free-form human-readable pointer (e.g.
    ``"hru-data.hru:row=42"`` or ``"outputs.basin_wb_aa"``); ``evidence``
    supplies the substitution mapping for the rule's ``message`` template
    and is also attached verbatim to the finding for downstream callers.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    location: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


CheckFn = Callable[
    ["TxtInOutProject"],
    "CheckResult | list[CheckResult] | None",
]

_CHECKS: dict[str, CheckFn] = {}


def register_check(name: str) -> Callable[[CheckFn], CheckFn]:
    """Decorator: register a check function under ``name``.

    Raises :class:`ValueError` if ``name`` is already registered, so
    typos and accidental double-registration fail fast at import time.
    """

    def decorator(fn: CheckFn) -> CheckFn:
        if name in _CHECKS:
            raise ValueError(f"Check already registered: {name!r}")
        _CHECKS[name] = fn
        return fn

    return decorator


def get_check(name: str) -> CheckFn:
    """Look up a registered check function; raise ``KeyError`` if missing."""
    try:
        return _CHECKS[name]
    except KeyError as exc:
        raise KeyError(f"No check registered under name {name!r}") from exc


__all__ = ["CheckFn", "CheckResult", "get_check", "register_check"]
