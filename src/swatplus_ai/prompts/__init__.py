"""Prompt assembly layer.

Public surface:

* :func:`build_module1_prompt` — render Module 1's two-message
  (system + user) conversation from findings, a project summary, and
  optional static passages.
* :func:`build_grounded_module1_prompt` — same as
  :func:`build_module1_prompt`, but fetches static passages from the
  retrieval layer first so ``[doc:<id>]`` citations in the reply are
  validated against the real I/O-spec corpus.
* :func:`retrieve_passages_for_findings` — the retrieval step on its
  own, for callers that want to interleave other work between the
  retrieval call and the prompt assembly.
* :class:`ProjectSummary` — condensed view of a parsed
  :class:`~swatplus_ai.parser.txtinout.TxtInOutProject` suitable for
  inlining in a prompt.
* :class:`StaticPassage` — contract for a single documentation snippet
  supplied to the assembler (populated by the retrieval layer).
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
from swatplus_ai.prompts.grounding import (
    build_grounded_module1_prompt,
    retrieve_passages_for_findings,
)

__all__ = [
    "Citation",
    "FormattedResponse",
    "ProjectSummary",
    "StaticPassage",
    "build_grounded_module1_prompt",
    "build_module1_prompt",
    "collect_handles",
    "format_module1_response",
    "retrieve_passages_for_findings",
]
