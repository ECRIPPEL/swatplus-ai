"""Unit tests for the grounding composition layer.

These tests never touch the real retrieval layer — every test injects
a fake ``retriever`` callable so we can pin the dedup / cap / failure-
mode contracts deterministically. An end-to-end test exercising the
real BM25 index lives in ``test_grounding_e2e.py``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.prompts.builder import ProjectSummary, StaticPassage
from swatplus_ai.prompts.formatter import collect_handles, format_module1_response
from swatplus_ai.prompts.grounding import (
    DEFAULT_MAX_PASSAGES,
    build_grounded_module1_prompt,
    retrieve_passages_for_findings,
)
from swatplus_ai.retrieval import RetrievedPassage


def _passage(handle: str, score: float, text: str = "body text") -> RetrievedPassage:
    return RetrievedPassage(
        handle=handle,
        text=text,
        score=score,
        source_ref="https://swatplus.gitbook.io/io-docs/llms-full.txt",
        metadata={"file": "time.sim", "section": "day-start"},
    )


def _recording_retriever(
    script: dict[str, tuple[RetrievedPassage, ...]],
) -> tuple[Callable[[str, int], tuple[RetrievedPassage, ...]], list[str]]:
    """Return a fake retriever + the list it records queries into."""
    seen: list[str] = []

    def _fn(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        seen.append(query)
        # Match against rule id prefix — every test controls the keying
        # via the rule id so we don't have to exact-match whole queries.
        for key, hits in script.items():
            if query.startswith(key):
                return hits[:k]
        return ()

    return _fn, seen


def test_empty_findings_returns_empty_without_calling_retriever(
    summary: ProjectSummary,
) -> None:
    retriever, seen = _recording_retriever({})
    passages = retrieve_passages_for_findings([], retriever=retriever)
    assert passages == ()
    assert seen == []


def test_single_finding_hits_are_converted_to_static_passages(
    summary: ProjectSummary,
    error_a: Finding,
) -> None:
    retriever, _ = _recording_retriever(
        {
            "setup.files_present": (
                _passage("doc:io:time.sim:day-start", 1.5, "The day_start field ..."),
                _passage("doc:io:time.sim:day-end", 1.2, "The day_end field ..."),
            ),
        }
    )
    passages = retrieve_passages_for_findings([error_a], retriever=retriever)
    assert len(passages) == 2
    # The ``doc:`` marker prefix is stripped; the ``io:`` source segment
    # stays intact so future corpora (litdb) key off the prefix cleanly.
    ids = [p.id for p in passages]
    assert ids == ["io:time.sim:day-start", "io:time.sim:day-end"]
    # Field mapping is stable: handle → id (stripped), text → body,
    # source_ref → source.
    top = passages[0]
    assert top.body == "The day_start field ..."
    assert top.source.startswith("https://")
    assert isinstance(top, StaticPassage)


def test_handles_dedup_across_findings_highest_score_wins(
    error_a: Finding,
    error_b: Finding,
) -> None:
    shared_handle = "doc:io:time.sim:day-start"
    shared_id = "io:time.sim:day-start"  # after ``doc:`` strip
    retriever, _ = _recording_retriever(
        {
            "setup.files_present": (_passage(shared_handle, 0.9, "low"),),
            "chan.routing_topology": (_passage(shared_handle, 2.1, "high"),),
        }
    )
    passages = retrieve_passages_for_findings([error_a, error_b], retriever=retriever)
    assert len(passages) == 1
    # Deduped to one entry; the higher-scoring body wins.
    assert passages[0].id == shared_id
    assert passages[0].body == "high"


def test_max_passages_caps_total_by_score(
    error_a: Finding,
    error_b: Finding,
    warning_a: Finding,
) -> None:
    retriever, _ = _recording_retriever(
        {
            "setup.files_present": (
                _passage("doc:io:a:1", 5.0),
                _passage("doc:io:a:2", 4.0),
                _passage("doc:io:a:3", 3.0),
            ),
            "chan.routing_topology": (
                _passage("doc:io:b:1", 4.5),
                _passage("doc:io:b:2", 3.5),
                _passage("doc:io:b:3", 2.5),
            ),
            "setup.warmup_ratio": (
                _passage("doc:io:c:1", 1.0),
                _passage("doc:io:c:2", 0.5),
                _passage("doc:io:c:3", 0.1),
            ),
        }
    )
    passages = retrieve_passages_for_findings(
        [error_a, error_b, warning_a],
        retriever=retriever,
        max_passages=4,
    )
    assert len(passages) == 4
    # Sorted strictly by score desc globally, not per-finding. Ids
    # carry no ``doc:`` prefix — that is marker syntax, stripped by
    # the grounding layer before passage construction.
    assert [p.id for p in passages] == [
        "io:a:1",
        "io:b:1",
        "io:a:2",
        "io:b:2",
    ]


def test_retriever_exception_on_one_finding_swallowed(
    error_a: Finding,
    error_b: Finding,
) -> None:
    calls: list[str] = []

    def _flaky(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        calls.append(query)
        if query.startswith("setup.files_present"):
            raise RuntimeError("network blip")
        return (_passage("doc:io:chandeg.con:out", 1.0),)

    passages = retrieve_passages_for_findings([error_a, error_b], retriever=_flaky)
    # Second finding's retrieval still contributed.
    assert len(passages) == 1
    assert passages[0].id == "io:chandeg.con:out"
    # Both retrievals were attempted — the exception didn't short-circuit.
    assert len(calls) == 2


def test_retriever_exception_on_every_finding_returns_empty(
    error_a: Finding, error_b: Finding
) -> None:
    def _blown(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        raise OSError("corpus not reachable")

    passages = retrieve_passages_for_findings([error_a, error_b], retriever=_blown)
    assert passages == ()


def test_empty_retrieval_returns_empty(error_a: Finding) -> None:
    retriever, _ = _recording_retriever({})  # always returns ()
    passages = retrieve_passages_for_findings([error_a], retriever=retriever)
    assert passages == ()


def test_k_is_forwarded_to_retriever(error_a: Finding) -> None:
    calls: list[int] = []

    def _recorder(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        calls.append(k)
        return ()

    retrieve_passages_for_findings([error_a], k=7, retriever=_recorder)
    assert calls == [7]


def test_default_max_passages_is_sensible() -> None:
    # Pin the default so callers can rely on it when sizing context.
    assert DEFAULT_MAX_PASSAGES == 12


def test_build_grounded_returns_messages_and_passages(
    summary: ProjectSummary, error_a: Finding
) -> None:
    retriever, _ = _recording_retriever(
        {
            "setup.files_present": (_passage("doc:io:time.sim:day-start", 1.0, "day_start body"),),
        }
    )
    messages, passages = build_grounded_module1_prompt([error_a], summary, retriever=retriever)
    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[1].role == "user"
    # The retrieved passage is inlined in the system prompt under its
    # bare (``doc:``-stripped) id — the builder's static-passages
    # renderer writes ``## [io:time.sim:day-start] <title>``.
    assert "io:time.sim:day-start" in messages[0].content
    assert "day_start body" in messages[0].content
    assert len(passages) == 1
    assert passages[0].id == "io:time.sim:day-start"


def test_build_grounded_with_empty_retrieval_still_produces_prompt(
    summary: ProjectSummary, error_a: Finding
) -> None:
    def _empty(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        return ()

    messages, passages = build_grounded_module1_prompt([error_a], summary, retriever=_empty)
    assert passages == ()
    # Static-passages section renders the "None provided." sentinel so
    # the LLM knows it saw no retrieval, not a truncation.
    assert "None provided." in messages[0].content


def test_build_grounded_with_retriever_exception_falls_back(
    summary: ProjectSummary, error_a: Finding
) -> None:
    def _blown(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        raise RuntimeError("retrieval is down")

    messages, passages = build_grounded_module1_prompt([error_a], summary, retriever=_blown)
    # No crash, no passages, prompt still assembled.
    assert passages == ()
    assert "None provided." in messages[0].content


def test_retrieved_handle_passes_formatter(summary: ProjectSummary, error_a: Finding) -> None:
    """Handles from the retrieved set validate as known citations."""
    retriever, _ = _recording_retriever(
        {
            "setup.files_present": (_passage("doc:io:time.sim:day-start", 1.0),),
        }
    )
    _, passages = build_grounded_module1_prompt([error_a], summary, retriever=retriever)
    known = collect_handles([error_a], passages)
    reply = "Refer to [doc:io:time.sim:day-start] for day_start semantics."
    formatted = format_module1_response(reply, known)
    assert formatted.unknown_citations == ()
    assert len(formatted.citations) == 1
    # The captured handle is the bare form — ``doc:`` is marker syntax.
    assert formatted.citations[0].handle == "io:time.sim:day-start"


def test_fabricated_handle_flagged_against_retrieved_set(
    summary: ProjectSummary, error_a: Finding
) -> None:
    """A handle not in the retrieved set is marked unknown."""
    retriever, _ = _recording_retriever(
        {
            "setup.files_present": (_passage("doc:io:time.sim:day-start", 1.0),),
        }
    )
    _, passages = build_grounded_module1_prompt([error_a], summary, retriever=retriever)
    known = collect_handles([error_a], passages)
    reply = "See [doc:io:time.sim:day-start] and also [doc:io:fake.ref:invented]."
    formatted = format_module1_response(reply, known)
    assert formatted.unknown_citations == ("io:fake.ref:invented",)


def test_empty_retrieved_set_flags_every_citation_as_unknown(
    summary: ProjectSummary, error_b: Finding
) -> None:
    """When retrieval yields nothing, every cited handle is unknown.

    ``error_b`` has ``references=()`` by construction so the only way
    a reply citation can be ``known`` is via static passages; with no
    passages retrieved and no finding-level refs, the formatter flags
    every cited handle.
    """

    def _empty(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        return ()

    _, passages = build_grounded_module1_prompt([error_b], summary, retriever=_empty)
    known = collect_handles([error_b], passages)
    reply = "The topology citation is [doc:io:chandeg.con:cycle]."
    formatted = format_module1_response(reply, known)
    assert formatted.unknown_citations == ("io:chandeg.con:cycle",)


def test_query_embeds_rule_id_and_message(error_a: Finding, warning_a: Finding) -> None:
    """The query passed to the retriever embeds rule id + finding message."""
    captured: list[str] = []

    def _recorder(query: str, k: int = 3) -> tuple[RetrievedPassage, ...]:
        captured.append(query)
        return ()

    retrieve_passages_for_findings([error_a, warning_a], retriever=_recorder)
    assert len(captured) == 2
    assert "setup.files_present" in captured[0]
    assert "Required file missing" in captured[0]
    assert "setup.warmup_ratio" in captured[1]
    assert "Warm-up" in captured[1]


def _as_sequence(items: Sequence[Finding]) -> Sequence[Finding]:
    # Helper so mypy doesn't flatten list[Finding] → Sequence[Finding]
    # incorrectly when we pass literal lists to the API.
    return items
