"""Prompt assembly layer.

Public surface:

* :func:`build_module1_prompt` — render Module 1's two-message
  (system + user) conversation from findings, a project summary, and
  optional static passages.
* :class:`ProjectSummary` — condensed view of a parsed
  :class:`~swatplus_ai.parser.txtinout.TxtInOutProject` suitable for
  inlining in a prompt.
* :class:`StaticPassage` — contract for a single documentation snippet
  supplied to the assembler (retrieval arrives in Phase 2).
"""

from __future__ import annotations

from swatplus_ai.prompts.builder import ProjectSummary, StaticPassage, build_module1_prompt

__all__ = ["ProjectSummary", "StaticPassage", "build_module1_prompt"]
