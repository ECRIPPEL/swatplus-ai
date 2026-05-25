"""BM25 index over a :class:`~swatplus_ai.retrieval.types.Chunk` corpus.

Thin wrapper around :class:`rank_bm25.BM25Okapi` — we bring our own
corpus bookkeeping (the chunk list stays in Python memory, not inside
the BM25 object) so persistence is "pickle the index + the chunks
tuple" rather than a bespoke serialisation dance. BM25 was chosen over
embeddings for slice R1 because it is:

* zero-extra-dep beyond ``rank-bm25`` (pure Python, no torch, no ONNX);
* deterministic (same corpus → same scores), so citation handles
  remain reproducible across re-indexing;
* fast enough at I/O-docs scale (single thousands of chunks) that
  query latency stays well under the LLM roundtrip floor.

Hybrid embedding rerank is a later slice (R3+); the index interface
below is deliberately narrow enough to let that land as a new class
rather than a surgery on this one.
"""

from __future__ import annotations

import pickle
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Final

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped, unused-ignore]

from swatplus_ai.retrieval.types import Chunk

_TOKEN_RE: Final = re.compile(r"[a-z0-9_]+")

_PICKLE_PROTOCOL: Final = 4


def tokenize(text: str) -> list[str]:
    """Lowercase + ``[a-z0-9_]+`` tokenizer shared by indexing and query.

    Intentionally minimal — no stemming, no stopword removal. Both
    would help recall on natural-language queries but would also make
    scores drift when the rank-bm25 / NLTK / whatever upstream dep
    retunes its defaults. For R1 the corpus is short, technical, and
    full of literal identifiers (``day_lag_max``, ``print.prt``); a
    dumb tokenizer matches those verbatim.
    """
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    """In-memory BM25 index with pickle-based persistence.

    The typical lifecycle is ``build`` once per corpus, ``save`` it,
    then ``load`` + ``search`` thereafter. ``build`` and ``load`` are
    mutually exclusive — calling one after the other replaces the
    backing state wholesale.
    """

    def __init__(self) -> None:
        self._chunks: tuple[Chunk, ...] = ()
        self._bm25: BM25Okapi | None = None

    @property
    def size(self) -> int:
        """Number of chunks currently indexed."""
        return len(self._chunks)

    def build(self, chunks: Iterable[Chunk]) -> None:
        """Index ``chunks``. Replaces any existing state."""
        materialised = tuple(chunks)
        tokenised = [tokenize(chunk.text) for chunk in materialised]
        if not tokenised:
            # rank_bm25 raises ZeroDivisionError on an empty corpus;
            # guard explicitly so callers see a stable shape instead.
            self._chunks = ()
            self._bm25 = None
            return
        self._chunks = materialised
        self._bm25 = BM25Okapi(tokenised)

    def search(
        self,
        query: str,
        *,
        k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> tuple[tuple[Chunk, float], ...]:
        """Return the top-``k`` ``(chunk, score)`` pairs for ``query``.

        ``filters`` is a metadata-equality predicate — e.g.
        ``{"file": "print.prt"}`` returns only chunks whose
        ``metadata["file"]`` equals ``"print.prt"``. Filtering happens
        *before* ranking so a narrow filter still gets ``k`` results
        when available (instead of the filter silently shrinking the
        already-truncated top-``k`` list).

        Chunks whose BM25 score is zero (no query term overlap at all)
        are dropped — returning them would be noise, not retrieval.
        An empty or whitespace-only query short-circuits to an empty
        tuple before hitting the BM25 machinery.
        """
        if self._bm25 is None or not self._chunks:
            return ()
        query_tokens = tokenize(query)
        if not query_tokens:
            return ()

        candidate_indices = self._candidate_indices(filters)
        if not candidate_indices:
            return ()

        scores = self._bm25.get_scores(query_tokens)
        scored = [(idx, float(scores[idx])) for idx in candidate_indices]
        scored = [(idx, score) for idx, score in scored if score > 0.0]
        scored.sort(key=lambda pair: pair[1], reverse=True)

        return tuple((self._chunks[idx], score) for idx, score in scored[:k])

    def save(self, path: Path) -> None:
        """Persist the index (chunks + BM25 state) to ``path`` via pickle.

        Pickle is fine for R1 — the format is "our own working copy",
        not a cross-process contract. When embeddings land in R3+ the
        durable format will be revisited (likely sqlite + a schema).
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(
                {"chunks": self._chunks, "bm25": self._bm25},
                fh,
                protocol=_PICKLE_PROTOCOL,
            )

    def load(self, path: Path) -> None:
        """Restore the index from a file written by :meth:`save`."""
        with path.open("rb") as fh:
            payload = pickle.load(fh)
        chunks = payload["chunks"]
        bm25 = payload["bm25"]
        if not isinstance(chunks, tuple):
            raise ValueError(f"invalid BM25 cache at {path}: chunks not a tuple")
        self._chunks = chunks
        self._bm25 = bm25

    def _candidate_indices(self, filters: Mapping[str, Any] | None) -> list[int]:
        if not filters:
            return list(range(len(self._chunks)))
        return [idx for idx, chunk in enumerate(self._chunks) if _matches_filter(chunk, filters)]


def _matches_filter(chunk: Chunk, filters: Mapping[str, Any]) -> bool:
    return all(chunk.metadata.get(key) == expected for key, expected in filters.items())
