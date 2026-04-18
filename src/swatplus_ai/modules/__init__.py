"""High-level user-facing modules that stitch parser + diagnostics + LLM.

The ``modules`` package is where SWAT+ai's command-scoped orchestrators
live. Each module owns one CLI verb end-to-end: parsing the project,
running the relevant diagnostic rules, optionally calling the LLM, and
assembling a structured result the CLI renders.

Public surface so far:

* :class:`SetupCheckResult` — frozen result bundle for ``swatplus-ai
  check``.
* :func:`run_setup_check` — async orchestrator; returns a result.
* :func:`render_setup_check_result` — Rich renderer that prints the
  result to a ``rich.console.Console``.
"""

from __future__ import annotations

from swatplus_ai.modules.setup_check import (
    SetupCheckResult,
    render_setup_check_result,
    run_setup_check,
)

__all__ = [
    "SetupCheckResult",
    "render_setup_check_result",
    "run_setup_check",
]
