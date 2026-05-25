"""Public retrieval entry point: :func:`retrieve`.

Orchestrates the three retrieval primitives — fetcher
(:mod:`swatplus_ai.retrieval.sources.io_docs`), chunker
(:mod:`swatplus_ai.retrieval.chunking.io_spec`), and BM25 index
(:mod:`swatplus_ai.retrieval.index.bm25`) — behind a single stable
signature that the prompt chat's Module 1 integration will consume.

The contract is deliberately narrow: one source (SWAT+ I/O spec), one
ranker (BM25), one handle shape (``doc:io:<file>:<slug>`` or the
sub-chunk variant with a fourth segment). Embeddings, hybrid rerank,
and the Phase 2 litdb source arrive as new public entry points in
later slices — not as extra kwargs on this one.
"""

from __future__ import annotations

import hashlib
import pickle
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from swatplus_ai.retrieval.chunking.io_spec import chunk_io_docs
from swatplus_ai.retrieval.index.bm25 import BM25Index
from swatplus_ai.retrieval.sources.io_docs import IO_DOCS_URL, fetch_io_docs
from swatplus_ai.retrieval.types import Chunk, RetrievedPassage

_INDEX_FILENAME: Final = "bm25_index.pkl"
_DEFAULT_CACHE_SUBDIR: Final = Path("data") / "retrieval" / "io_docs"


def retrieve(
    query: str,
    k: int = 5,
    filters: Mapping[str, Any] | None = None,
    *,
    cache_dir: Path | None = None,
) -> tuple[RetrievedPassage, ...]:
    """Top-``k`` passage retrieval over the SWAT+ I/O spec corpus.

    First call from a cold ``cache_dir`` performs a network fetch of
    the gitbook ``llms-full.txt`` dump, chunks it into retrievable
    sections, builds a BM25 index, and persists everything under
    ``cache_dir``. Subsequent calls reuse the cached corpus + index
    whenever the corpus SHA-256 still matches. A corpus refresh (new
    gitbook content) automatically invalidates and rebuilds the index.

    :param query: Free-form text query. Tokenised with the same rule
        the index used.
    :param k: Maximum number of passages to return. Passes with BM25
        score ``0`` are always dropped, so ``k`` is an upper bound.
    :param filters: Optional metadata equality predicate. R1 supports
        ``{"file": "<swatplus_file>"}`` to restrict to chunks from a
        single SWAT+ file (e.g. ``"print.prt"``).
    :param cache_dir: Directory for the corpus + index cache. Defaults
        to ``<cwd>/data/retrieval/io_docs``. Tests pass a ``tmp_path``.
    :returns: Tuple of :class:`RetrievedPassage`, ordered by descending
        BM25 score. Empty when the query is empty, the corpus contains
        no matching tokens, or the filter eliminates every candidate.
    """
    resolved_cache = cache_dir if cache_dir is not None else _default_cache_dir()
    corpus_path = fetch_io_docs(resolved_cache)
    index = _load_or_build_index(corpus_path, resolved_cache)

    hits = index.search(query, k=k, filters=filters)
    return tuple(_to_passage(chunk, score) for chunk, score in hits)


def _default_cache_dir() -> Path:
    return Path.cwd() / _DEFAULT_CACHE_SUBDIR


def _load_or_build_index(corpus_path: Path, cache_dir: Path) -> BM25Index:
    index_path = cache_dir / _INDEX_FILENAME
    corpus_sha = _sha256_of(corpus_path)
    if index_path.is_file() and _cached_index_matches(index_path, corpus_sha):
        index = BM25Index()
        try:
            index.load(index_path)
            return index
        except (pickle.UnpicklingError, ValueError, EOFError, KeyError):
            # Corrupt or legacy cache — fall through to rebuild.
            pass
    return _rebuild_index(corpus_path, index_path, corpus_sha)


def _cached_index_matches(index_path: Path, corpus_sha: str) -> bool:
    try:
        with index_path.open("rb") as fh:
            payload = pickle.load(fh)
    except (pickle.UnpicklingError, OSError, EOFError):
        return False
    return isinstance(payload, dict) and payload.get("corpus_sha") == corpus_sha


def _rebuild_index(corpus_path: Path, index_path: Path, corpus_sha: str) -> BM25Index:
    chunks = chunk_io_docs(corpus_path, source_ref=IO_DOCS_URL)
    index = BM25Index()
    index.build(chunks)
    index.save(index_path)
    _stamp_corpus_sha(index_path, corpus_sha)
    return index


def _stamp_corpus_sha(index_path: Path, corpus_sha: str) -> None:
    # BM25Index.save writes a pickled dict with chunks + bm25; we
    # re-open it to add the corpus_sha key so future loads can check
    # cache validity without a separate sidecar file.
    with index_path.open("rb") as fh:
        payload = pickle.load(fh)
    payload["corpus_sha"] = corpus_sha
    with index_path.open("wb") as fh:
        pickle.dump(payload, fh, protocol=4)


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _to_passage(chunk: Chunk, score: float) -> RetrievedPassage:
    metadata = dict(chunk.metadata)
    source_ref = str(metadata.pop("source_ref", IO_DOCS_URL))
    return RetrievedPassage(
        handle=chunk.handle,
        text=chunk.text,
        score=score,
        source_ref=source_ref,
        metadata=metadata,
    )
