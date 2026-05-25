"""End-to-end pins for :func:`swatplus_ai.retrieval.retrieve`.

Every test primes the cache directory with the committed fixture and
a matching manifest so the fetcher's SHA check short-circuits to the
cache. No network traffic is allowed — if a test accidentally triggers
an HTTP request, the missing ``httpx.get`` monkeypatch will surface as
a real-world failure and the suite won't silently depend on gitbook
uptime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from swatplus_ai.retrieval import RetrievedPassage, retrieve
from swatplus_ai.retrieval.sources.io_docs import IO_DOCS_URL

_FIXTURE = Path(__file__).parent / "fixtures" / "io_docs_excerpt.txt"


@pytest.fixture
def primed_cache(tmp_path: Path) -> Path:
    """Return a cache_dir pre-populated with the committed fixture.

    The fetcher's SHA check will succeed, so ``retrieve`` never
    attempts a network call during the test.
    """
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
    """Hard guard: any attempt at HTTP from this module fails loudly."""
    from swatplus_ai.retrieval.sources import io_docs

    def blown(url: str, **kwargs: object) -> None:
        raise AssertionError(f"retrieve() attempted HTTP GET {url}; cache prime failed")

    monkeypatch.setattr(io_docs.httpx, "get", blown)


def test_retrieve_end_to_end_returns_passages(primed_cache: Path) -> None:
    results = retrieve("day_start beginning day simulation", cache_dir=primed_cache)
    assert results, "expected at least one hit for day_start query"
    assert all(isinstance(passage, RetrievedPassage) for passage in results)
    top = results[0]
    assert top.handle.startswith("doc:io:")
    assert top.score > 0.0
    # source_ref is promoted out of metadata into the passage shape.
    assert top.source_ref.startswith("https://")
    assert "source_ref" not in top.metadata


def test_retrieve_respects_k(primed_cache: Path) -> None:
    results = retrieve("simulation", k=2, cache_dir=primed_cache)
    assert len(results) <= 2


def test_retrieve_with_file_filter(primed_cache: Path) -> None:
    results = retrieve(
        "day",
        k=5,
        filters={"file": "time.sim"},
        cache_dir=primed_cache,
    )
    assert results, "filter should still match at least one time.sim chunk"
    assert all(passage.metadata.get("file") == "time.sim" for passage in results)


def test_retrieve_scores_are_descending(primed_cache: Path) -> None:
    results = retrieve("print output", k=5, cache_dir=primed_cache)
    scores = [passage.score for passage in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_caches_index_file_after_first_call(primed_cache: Path) -> None:
    index_path = primed_cache / "bm25_index.pkl"
    assert not index_path.exists()
    retrieve("day_start", cache_dir=primed_cache)
    assert index_path.is_file()


def test_retrieve_reuses_cached_index(primed_cache: Path) -> None:
    retrieve("day_start", cache_dir=primed_cache)
    index_path = primed_cache / "bm25_index.pkl"
    first_mtime = index_path.stat().st_mtime_ns
    # Second call with an identical corpus should not rebuild the index.
    retrieve("day_end", cache_dir=primed_cache)
    assert index_path.stat().st_mtime_ns == first_mtime


def test_retrieve_rebuilds_when_index_stale(primed_cache: Path) -> None:
    retrieve("day_start", cache_dir=primed_cache)
    index_path = primed_cache / "bm25_index.pkl"
    # Simulate a corpus change: overwrite corpus + manifest with a new
    # payload (still structurally valid markdown so the chunker works).
    new_payload = b"# time.sim\n\nA minimal replacement corpus.\n"
    (primed_cache / "llms-full.txt").write_bytes(new_payload)
    manifest = {
        "url": IO_DOCS_URL,
        "sha256": hashlib.sha256(new_payload).hexdigest(),
        "size_bytes": len(new_payload),
        "fetched_at": "2026-04-21T01:00:00Z",
    }
    (primed_cache / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    before = index_path.read_bytes()
    retrieve("time.sim", cache_dir=primed_cache)
    after = index_path.read_bytes()
    assert before != after, "index pickle should rebuild when corpus sha changes"


def test_retrieve_empty_query_returns_empty(primed_cache: Path) -> None:
    assert retrieve("", cache_dir=primed_cache) == ()


def test_retrieve_unknown_term_returns_empty(primed_cache: Path) -> None:
    assert retrieve("zzzzznonexistentterm", cache_dir=primed_cache) == ()
