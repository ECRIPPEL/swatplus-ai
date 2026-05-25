"""Retrieval-augmented grounding for SWAT+ai (Phase 1 / 2).

Public surface:

* :func:`retrieve` — top-``k`` BM25 retrieval over the SWAT+ I/O spec
  corpus. First call fetches + chunks + indexes; subsequent calls hit
  the cache.
* :class:`RetrievedPassage` — frozen contract for each returned
  passage, carrying the stable citation handle that the Module 1
  response formatter validates.

Not re-exported: the internal :class:`~swatplus_ai.retrieval.types.Chunk`
dataclass, the BM25 wrapper, and the source-specific fetcher are
accessible via their sub-modules but are implementation details. The
prompt chat's Module 1 integration should depend on the two names
below and nothing else.

Slice R1 scope (see ``dogfood/BRIEF_R1.md``): I/O spec only, BM25 only,
no embeddings, no litdb, no hybrid rerank. Those arrive in later
slices as *additions* to this surface, not modifications.
"""

from __future__ import annotations

from swatplus_ai.retrieval.api import retrieve
from swatplus_ai.retrieval.types import RetrievedPassage

__all__ = ["RetrievedPassage", "retrieve"]
