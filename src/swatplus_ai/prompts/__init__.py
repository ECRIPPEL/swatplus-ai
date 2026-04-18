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
* :func:`format_module1_response` / :func:`collect_handles` — parse
  inline ``[doc:<id>]`` citations from a raw LLM response and validate
  them against the handles visible at prompt time.
* :class:`Citation` / :class:`FormattedResponse` — frozen outputs of
  the response formatter.
"""

from __future__ import annotations

from swatplus_ai.prompts.builder import ProjectSummary, StaticPassage, build_module1_prompt
from swatplus_ai.prompts.formatter import (
    Citation,
    FormattedResponse,
    collect_handles,
    format_module1_response,
)

__all__ = [
    "Citation",
    "FormattedResponse",
    "ProjectSummary",
    "StaticPassage",
    "build_module1_prompt",
    "collect_handles",
    "format_module1_response",
]
