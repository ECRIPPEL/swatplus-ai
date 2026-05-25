"""Frozen data contracts for the retrieval layer.

:class:`RetrievedPassage` is the *external* shape — what callers (the
prompt chat's Module 1 integration, any future module) receive from
:func:`swatplus_ai.retrieval.retrieve`. Its ``handle`` is a stable
citation token the Module 1 formatter validates against an allowlist;
every field is pinned by the retrieval API contract.

:class:`Chunk` is the *internal* shape — what the chunker produces and
the index stores. It carries everything needed to later materialise a
:class:`RetrievedPassage` plus a BM25 score. Consumers outside the
retrieval package should not depend on :class:`Chunk`; it may change
without a contract bump.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict


class RetrievedPassage(BaseModel):
    """A single passage returned by :func:`retrieve`.

    The ``handle`` is the project's citation primitive: a short,
    deterministic token of the form ``doc:<source>:<key>:<subkey>``
    that the Module 1 formatter matches against the prompt-time
    allowlist. If a handle changes between runs for the same underlying
    content, citations break — that invariant is pinned by
    :func:`tests.retrieval.test_io_spec_chunker.test_chunker_handles_are_deterministic`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handle: str
    text: str
    score: float
    source_ref: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class Chunk:
    """Internal chunk record produced by a chunker and stored in the index.

    ``metadata`` is deliberately permissive — different sources carry
    different metadata shapes (``file`` + ``section`` for I/O docs,
    ``doi`` + ``year`` for the future litdb source, etc.). The retrieval
    API only requires the three core fields below plus whatever the
    source-specific :func:`chunk_*` function chooses to attach.
    """

    handle: str
    text: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
