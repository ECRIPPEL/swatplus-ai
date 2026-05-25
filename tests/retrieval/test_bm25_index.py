"""BM25 index lifecycle pins: build → search → save → load."""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.retrieval.index.bm25 import BM25Index, tokenize
from swatplus_ai.retrieval.types import Chunk


def _make_corpus() -> tuple[Chunk, ...]:
    return (
        Chunk(
            handle="doc:io:time.sim:day-start",
            text="# day_start\n\nBeginning day of the simulation.",
            metadata={"file": "time.sim"},
        ),
        Chunk(
            handle="doc:io:time.sim:day-end",
            text="# day_end\n\nEnding day of the simulation.",
            metadata={"file": "time.sim"},
        ),
        Chunk(
            handle="doc:io:print.prt:nyskip",
            text="# nyskip\n\nNumber of years to skip at the beginning.",
            metadata={"file": "print.prt"},
        ),
        Chunk(
            handle="doc:io:parameters.bsn:day-lag-max",
            text="# day_lag_max\n\nMaximum number of days for surface runoff lag.",
            metadata={"file": "parameters.bsn"},
        ),
        Chunk(
            handle="doc:io:_general:intro",
            text="# Introduction\n\nWelcome to SWAT+, a watershed model.",
            metadata={"file": "_general"},
        ),
    )


def test_tokenize_keeps_underscored_identifiers() -> None:
    assert tokenize("day_lag_max is 7") == ["day_lag_max", "is", "7"]
    assert tokenize("Print.PRT") == ["print", "prt"]


def test_build_and_search_top_match_is_expected() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    results = index.search("day_lag_max surface runoff lag")
    assert results, "expected at least one scored hit"
    top_chunk, top_score = results[0]
    assert top_chunk.handle == "doc:io:parameters.bsn:day-lag-max"
    assert top_score > 0.0


def test_search_results_are_score_ordered() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    results = index.search("day simulation beginning")
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_search_respects_k() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    results = index.search("simulation", k=2)
    assert len(results) <= 2


def test_search_empty_query_returns_empty() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    assert index.search("") == ()
    assert index.search("   ") == ()


def test_search_with_file_filter() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    results = index.search("day", filters={"file": "time.sim"})
    assert results
    assert all(chunk.metadata["file"] == "time.sim" for chunk, _ in results)


def test_search_with_filter_matching_nothing_returns_empty() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    results = index.search("day", filters={"file": "does-not-exist.xyz"})
    assert results == ()


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    index = BM25Index()
    index.build(_make_corpus())
    target = tmp_path / "bm25.pkl"
    index.save(target)

    reloaded = BM25Index()
    reloaded.load(target)

    original = index.search("day_lag_max")
    restored = reloaded.search("day_lag_max")
    assert [c.handle for c, _ in original] == [c.handle for c, _ in restored]
    assert [round(s, 6) for _, s in original] == [round(s, 6) for _, s in restored]


def test_empty_corpus_does_not_crash() -> None:
    index = BM25Index()
    index.build(())
    assert index.search("anything") == ()
    assert index.size == 0


def test_size_reports_chunk_count() -> None:
    index = BM25Index()
    index.build(_make_corpus())
    assert index.size == len(_make_corpus())
