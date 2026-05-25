"""End-to-end pin: diagnostic findings → real BM25 → prompt → formatter.

Exercises the full grounding pipeline against the committed retrieval
fixture (same pattern as ``tests/retrieval/test_api.py``): fetcher is
short-circuited by a pre-populated cache dir, BM25 builds and ranks for
real, and the formatter validates citations against the handles that
actually came back from retrieval. No network, no LLM — the LLM reply
is a hand-written string that mentions one retrieved handle and one
invented one, so we can pin both the "real handle survives" and
"fabricated handle flagged" halves of the contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.prompts.builder import ProjectSummary
from swatplus_ai.prompts.formatter import collect_handles, format_module1_response
from swatplus_ai.prompts.grounding import build_grounded_module1_prompt
from swatplus_ai.retrieval import retrieve
from swatplus_ai.retrieval.sources.io_docs import IO_DOCS_URL

_FIXTURE = Path(__file__).parent.parent / "retrieval" / "fixtures" / "io_docs_excerpt.txt"


@pytest.fixture
def primed_cache(tmp_path: Path) -> Path:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    payload = _FIXTURE.read_bytes()
    (cache_dir / "llms-full.txt").write_bytes(payload)
    manifest = {
        "url": IO_DOCS_URL,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "fetched_at": "2026-04-21T00:00:00Z",
    }
    (cache_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return cache_dir


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any HTTP attempt in this file is a bug, not a warning."""
    from swatplus_ai.retrieval.sources import io_docs

    def blown(url: str, **kwargs: object) -> None:
        raise AssertionError(f"grounding e2e attempted HTTP GET {url}; cache prime failed")

    monkeypatch.setattr(io_docs.httpx, "get", blown)


def test_grounded_prompt_retrieves_real_passages_from_io_spec(
    primed_cache: Path,
) -> None:
    finding = Finding(
        id="setup.sim_period_sanity",
        severity="warning",
        location="time.sim",
        evidence={"day_start": 0, "day_end": 0},
        rule_ref="setup.sim_period_sanity",
        message=("day_start and day_end are both zero — simulation spans the full calendar year"),
        references=(),
    )
    summary = ProjectSummary(
        sim_start_year=2010,
        sim_end_year=2015,
        warmup_years=2,
        n_hrus=42,
        n_channels=5,
        n_aquifers=2,
        n_subbasins=3,
        pet_method=1,
        basin_area_km2=12.3,
    )

    retriever = partial_retriever(primed_cache)
    messages, passages = build_grounded_module1_prompt([finding], summary, retriever=retriever)

    assert passages, (
        "expected at least one real passage from the I/O spec fixture for a simulation-period query"
    )
    # Every id carries the I/O-spec source segment. The ``doc:`` marker
    # prefix has been stripped — it is citation syntax in the formatter,
    # not part of the handle the LLM validates against.
    for passage in passages:
        assert passage.id.startswith("io:"), f"unexpected handle shape: {passage.id}"
        assert passage.body, "retrieved passage should carry body text"
        assert passage.source.startswith("https://"), "source should propagate the retrieval URL"

    # The system message actually contains the retrieved handles — the
    # LLM sees them, not just a placeholder.
    system_content = messages[0].content
    assert "io:" in system_content


def test_formatter_accepts_retrieved_handle_and_flags_fabrication(
    primed_cache: Path,
) -> None:
    finding = Finding(
        id="setup.sim_period_sanity",
        severity="warning",
        location="time.sim",
        evidence={"day_start": 0, "day_end": 0},
        rule_ref="setup.sim_period_sanity",
        message="day_start and day_end are both zero",
        references=(),
    )
    summary = ProjectSummary(
        sim_start_year=2010,
        sim_end_year=2015,
        warmup_years=2,
        n_hrus=42,
        n_channels=5,
        n_aquifers=2,
        n_subbasins=3,
        pet_method=1,
        basin_area_km2=12.3,
    )
    retriever = partial_retriever(primed_cache)
    _, passages = build_grounded_module1_prompt([finding], summary, retriever=retriever)
    assert passages, "fixture should yield at least one passage"

    real_handle = passages[0].id  # bare (``doc:``-stripped) form
    fabricated_handle = "io:not.a.real:invented-section"
    reply = (
        f"The simulation window is defined in [doc:{real_handle}]. "
        f"See also [doc:{fabricated_handle}] for details."
    )

    known = collect_handles([finding], passages)
    formatted = format_module1_response(reply, known)

    real_hits = [c for c in formatted.citations if c.handle == real_handle]
    fake_hits = [c for c in formatted.citations if c.handle == fabricated_handle]
    assert len(real_hits) == 1
    assert len(fake_hits) == 1
    assert formatted.unknown_citations == (fabricated_handle,)


def test_empty_retrieval_for_gibberish_query_still_assembles(
    primed_cache: Path,
) -> None:
    """A finding whose message has no overlap with the corpus retrieves
    nothing — the prompt still assembles and the formatter reports every
    citation as unknown (retrieved set is empty, finding has no refs).
    """
    finding = Finding(
        id="setup.nonexistent",
        severity="info",
        location=None,
        evidence={},
        rule_ref="setup.nonexistent",
        message="zzzzznonexistentterm qqqqqqnonexistentotherterm",
        references=(),
    )
    summary = ProjectSummary(pet_method=1)
    retriever = partial_retriever(primed_cache)

    messages, passages = build_grounded_module1_prompt([finding], summary, retriever=retriever)
    assert passages == ()
    # Static-passages block renders the sentinel, not a truncation.
    assert "None provided." in messages[0].content

    known = collect_handles([finding], passages)
    reply = "See [doc:io:nowhere:anything] for the ground truth."
    formatted = format_module1_response(reply, known)
    # Captured handle is the bare form (``doc:`` is marker syntax).
    assert formatted.unknown_citations == ("io:nowhere:anything",)


def partial_retriever(cache_dir: Path):
    """Bind ``cache_dir`` into the real :func:`retrieve` so the grounding
    layer's ``(query, k)`` contract is satisfied while the fetcher reads
    from the primed fixture.
    """

    def _fn(query: str, k: int = 3):
        return retrieve(query, k=k, cache_dir=cache_dir)

    return _fn
