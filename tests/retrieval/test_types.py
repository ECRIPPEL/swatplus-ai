"""Frozen-contract pins for the retrieval data types."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from pydantic import ValidationError

from swatplus_ai.retrieval.types import Chunk, RetrievedPassage


def _make_passage() -> RetrievedPassage:
    return RetrievedPassage(
        handle="doc:io:time.sim:day-start",
        text="Beginning day of the simulation.",
        score=1.234,
        source_ref="https://swatplus.gitbook.io/io-docs/llms-full.txt",
        metadata={"file": "time.sim", "section": "day_start"},
    )


def test_retrieved_passage_is_frozen() -> None:
    passage = _make_passage()
    with pytest.raises(ValidationError):
        passage.handle = "doc:io:other:foo"  # type: ignore[misc]


def test_retrieved_passage_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RetrievedPassage(
            handle="doc:io:x:y",
            text="",
            score=0.0,
            source_ref="url",
            metadata={},
            rogue_field="nope",  # type: ignore[call-arg]
        )


def test_retrieved_passage_carries_handle_and_score() -> None:
    passage = _make_passage()
    assert passage.handle == "doc:io:time.sim:day-start"
    assert passage.score == pytest.approx(1.234)
    assert passage.metadata["file"] == "time.sim"


def test_chunk_metadata_defaults_empty() -> None:
    chunk = Chunk(handle="doc:io:_general:intro", text="Hello world")
    assert chunk.metadata == {}


def test_chunk_is_frozen_dataclass() -> None:
    chunk = Chunk(handle="doc:io:_general:intro", text="Hello", metadata={"a": 1})
    with pytest.raises(FrozenInstanceError):
        chunk.handle = "other"  # type: ignore[misc]
