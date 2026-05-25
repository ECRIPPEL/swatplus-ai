"""Retrieval-grounded Module 1 prompt composition.

This module is the single seam between the deterministic prompt
assembler (:mod:`swatplus_ai.prompts.builder`) and the retrieval layer
(:mod:`swatplus_ai.retrieval`). It turns a sequence of :class:`Finding`
objects into the set of :class:`StaticPassage` snippets the Module 1
prompt ships alongside them, so the LLM sees deterministic facts *plus*
I/O-spec excerpts and the formatter can validate ``[doc:<id>]``
citations against the exact set the model actually received.

Design notes:

* The retriever is injectable (``retriever=retrieve`` default) so unit
  tests monkeypatch in a fake without touching the retrieval package or
  the network. The signature ``(query, k)`` is a subset of the real
  :func:`swatplus_ai.retrieval.retrieve` signature — the grounding
  layer doesn't use ``filters`` or ``cache_dir`` today; integration
  tests inject a closure that pins ``cache_dir``.
* Query strategy V1 is intentionally coarse: one retrieval call per
  finding, ``k=3`` per call, dedup handles globally, cap the total at
  ``max_passages=12``. Refining the query (rule-specific templates,
  expansion, filtering by ``file``) waits for real dogfood signal —
  anything else is premature tuning.
* Degrades gracefully on every known failure mode of :func:`retrieve`:
  exception per call, empty tuple, empty findings. The ``check`` CLI
  must never crash because retrieval did — the pipeline falls back to
  an un-grounded prompt and the user still gets findings + a report.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Protocol

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.llm.interface import Message
from swatplus_ai.prompts.builder import (
    ProjectSummary,
    StaticPassage,
    build_module1_prompt,
)
from swatplus_ai.retrieval import RetrievedPassage, retrieve

_LOG = logging.getLogger(__name__)

DEFAULT_K_PER_FINDING = 3
DEFAULT_MAX_PASSAGES = 12


class Retriever(Protocol):
    """Structural type for the retrieval callable grounding depends on.

    Matches the positional-or-keyword ``(query, k)`` prefix of
    :func:`swatplus_ai.retrieval.retrieve`; integration tests pass a
    ``lambda q, k=3: retrieve(q, k=k, cache_dir=<tmp>)`` to pin cache.
    """

    def __call__(
        self,
        query: str,
        k: int = ...,
    ) -> tuple[RetrievedPassage, ...]: ...


def retrieve_passages_for_findings(
    findings: Sequence[Finding],
    *,
    k: int = DEFAULT_K_PER_FINDING,
    max_passages: int = DEFAULT_MAX_PASSAGES,
    retriever: Retriever = retrieve,
) -> tuple[StaticPassage, ...]:
    """Retrieve I/O-spec passages for every finding, dedup, cap.

    One retrieval call per finding with ``k`` hits each; passages with
    the same :attr:`RetrievedPassage.handle` are deduped across findings
    (highest BM25 score wins so downstream ranking stays honest); the
    global total is capped at ``max_passages`` by score to keep the
    prompt's ``Static reference passages`` block bounded regardless of
    basin scale.

    Exceptions from ``retriever`` are logged and swallowed per finding:
    a network blip or a corrupt cache must not kill the surrounding
    ``check`` run. Empty findings returns ``()`` without invoking
    ``retriever`` at all.
    """
    if not findings:
        return ()

    best: dict[str, RetrievedPassage] = {}
    for finding in findings:
        query = _finding_query(finding)
        if not query.strip():
            continue
        try:
            hits = retriever(query, k=k)
        except Exception as exc:
            _LOG.warning(
                "retrieval failed for rule %s: %s: %s",
                finding.id,
                type(exc).__name__,
                exc,
            )
            continue
        for passage in hits:
            prev = best.get(passage.handle)
            if prev is None or passage.score > prev.score:
                best[passage.handle] = passage

    ranked = sorted(best.values(), key=lambda p: p.score, reverse=True)
    capped = ranked[:max_passages]
    return tuple(_to_static_passage(p) for p in capped)


def build_grounded_module1_prompt(
    findings: Sequence[Finding],
    project_summary: ProjectSummary,
    *,
    k: int = DEFAULT_K_PER_FINDING,
    max_passages: int = DEFAULT_MAX_PASSAGES,
    retriever: Retriever = retrieve,
) -> tuple[list[Message], tuple[StaticPassage, ...]]:
    """Compose the retrieval step and the prompt assembler into one call.

    Returns ``(messages, passages)``. The caller hands ``messages``
    straight to an :class:`~swatplus_ai.llm.interface.LLMBackend` and
    feeds ``passages`` into
    :func:`swatplus_ai.prompts.formatter.collect_handles` alongside
    ``findings`` so the reply validator sees the same handle set the
    model was shown.
    """
    passages = retrieve_passages_for_findings(
        findings,
        k=k,
        max_passages=max_passages,
        retriever=retriever,
    )
    messages = build_module1_prompt(list(findings), project_summary, list(passages))
    return messages, passages


def _finding_query(finding: Finding) -> str:
    # Rule id (e.g. "setup.files_present") carries the topic; message
    # carries the specific facts ("Required file missing: time.sim").
    # Concatenating both gives BM25 enough signal without the noise of
    # evidence dicts or Python-side identifiers that a modeler wouldn't
    # grep the docs for.
    return f"{finding.id} {finding.message}"


def _to_static_passage(passage: RetrievedPassage) -> StaticPassage:
    meta = passage.metadata
    # Prefer the markdown section title when the chunker captured one;
    # fall back to the SWAT+ filename the chunk came from; last resort
    # is the handle itself so the block always has a non-empty title.
    title_candidate = meta.get("section") or meta.get("file") or passage.handle
    # Strip the ``doc:`` marker prefix: the formatter treats ``doc:`` as
    # citation syntax (``[doc:<id>]``), so the ``<id>`` stored on the
    # passage must be the bare form. The ``io:`` source segment stays
    # intact — that is how the formatter's handle allowlist will key off
    # source when Phase 2 adds the litdb corpus.
    handle_id = passage.handle.removeprefix("doc:")
    return StaticPassage(
        id=handle_id,
        title=str(title_candidate),
        body=passage.text,
        source=passage.source_ref,
    )


__all__ = [
    "DEFAULT_K_PER_FINDING",
    "DEFAULT_MAX_PASSAGES",
    "Retriever",
    "build_grounded_module1_prompt",
    "retrieve_passages_for_findings",
]
