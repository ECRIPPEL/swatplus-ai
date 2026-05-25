"""Structural pins for the SWAT+ I/O spec chunker.

Most tests run against the committed ``io_docs_excerpt.txt`` fixture
(first ~500 lines of a real ``llms-full.txt`` snapshot). The sub-split
and synthetic-handle tests use inline markdown so the threshold and
handle-concatenation behaviours are exercised deterministically — the
real fixture's section sizes drift whenever SWAT+ edits a page, and
we don't want to re-pin tests on every gitbook refresh.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from swatplus_ai.retrieval.chunking.io_spec import MAX_CHUNK_CHARS, chunk_io_docs
from swatplus_ai.retrieval.types import Chunk

_FIXTURE = Path(__file__).parent / "fixtures" / "io_docs_excerpt.txt"

_HANDLE_RE = re.compile(r"^doc:io:([a-z0-9._-]+):([a-z0-9-]+)(?::([a-z0-9-]+))?$")


def _chunks_from_fixture() -> tuple[Chunk, ...]:
    return chunk_io_docs(_FIXTURE)


def test_chunker_recognises_swatplus_files() -> None:
    chunks = _chunks_from_fixture()
    files_present = {chunk.metadata["file"] for chunk in chunks}
    # Each of these appears as a `# <filename>` header in the fixture.
    for expected in ("time.sim", "print.prt", "file.cio", "object.cnt"):
        assert expected in files_present, f"expected {expected} among {files_present}"


def test_field_pages_inherit_last_file_context() -> None:
    chunks = _chunks_from_fixture()
    by_handle = {chunk.handle: chunk for chunk in chunks}
    # `# day_start` appears after `# time.sim`, so it must inherit the
    # time.sim file context — never "_general".
    assert "doc:io:time.sim:day-start" in by_handle
    assert by_handle["doc:io:time.sim:day-start"].metadata["file"] == "time.sim"
    # Same for nyskip under print.prt.
    assert "doc:io:print.prt:nyskip" in by_handle
    assert by_handle["doc:io:print.prt:nyskip"].metadata["file"] == "print.prt"


def test_general_sections_use_general_marker() -> None:
    chunks = _chunks_from_fixture()
    # `# Introduction to SWAT+` precedes any file page, so it lives
    # under the _general sentinel.
    intro = next(
        (c for c in chunks if c.handle.startswith("doc:io:_general:introduction")),
        None,
    )
    assert intro is not None
    assert intro.metadata["file"] == "_general"


def test_master_file_detects_parens_filename() -> None:
    chunks = _chunks_from_fixture()
    # `# Master File (file.cio)` should be attributed to file.cio, not
    # split across a `_general` marker.
    cio_chunks = [c for c in chunks if c.metadata["file"] == "file.cio"]
    assert cio_chunks, "no chunks attributed to file.cio"
    # The first file.cio chunk's handle should encode the full section
    # title as a slug.
    assert any("master-file-file-cio" in c.handle for c in cio_chunks)


def test_all_handles_match_spec() -> None:
    chunks = _chunks_from_fixture()
    for chunk in chunks:
        assert _HANDLE_RE.match(chunk.handle), (
            f"handle {chunk.handle!r} violates doc:io:<file>:<slug>[:<sub>] shape"
        )


def test_chunker_handles_are_deterministic(tmp_path: Path) -> None:
    copy_path = tmp_path / "copy.txt"
    copy_path.write_bytes(_FIXTURE.read_bytes())
    first = chunk_io_docs(_FIXTURE)
    second = chunk_io_docs(copy_path)
    assert [c.handle for c in first] == [c.handle for c in second]


def test_chunker_preserves_title_in_text() -> None:
    chunks = _chunks_from_fixture()
    day_start = next(c for c in chunks if c.handle == "doc:io:time.sim:day-start")
    # The chunk text should include the original header so a retrieval
    # consumer sees the anchor alongside the body.
    assert day_start.text.startswith("# day")
    assert "Beginning day" in day_start.text


def test_slug_strips_markdown_escapes(tmp_path: Path) -> None:
    # Gitbook escapes underscores in field headers as ``day\_start``;
    # the slug must collapse the backslash so the handle is valid.
    src = tmp_path / "synthetic.txt"
    src.write_text("# time.sim\n\nA file page.\n\n# day\\_start\n\nBody.\n")
    chunks = chunk_io_docs(src)
    assert "doc:io:time.sim:day-start" in [c.handle for c in chunks]


def test_chunker_subsplits_large_sections(tmp_path: Path) -> None:
    big_body_a = "A " * (MAX_CHUNK_CHARS // 2)
    big_body_b = "B " * (MAX_CHUNK_CHARS // 2)
    src = tmp_path / "synthetic.txt"
    src.write_text(
        f"# Calibration\n\nIntro.\n\n"
        f"## Soft calibration procedure\n\n{big_body_a}\n\n"
        f"## Hard calibration procedure\n\n{big_body_b}\n"
    )
    chunks = chunk_io_docs(src)
    handles = [c.handle for c in chunks]
    # Two sub-chunks under the same parent, both with a sub-slug appended.
    assert "doc:io:_general:calibration:soft-calibration-procedure" in handles
    assert "doc:io:_general:calibration:hard-calibration-procedure" in handles
    # No unsplit parent-only chunk should survive when the threshold is exceeded.
    assert "doc:io:_general:calibration" not in handles


def test_chunker_keeps_small_section_whole(tmp_path: Path) -> None:
    src = tmp_path / "synthetic.txt"
    src.write_text(
        "# time.sim\n\nThis file controls the simulation time period.\n\n"
        "# day_start\n\nBeginning day.\n"
    )
    chunks = chunk_io_docs(src)
    handles = [c.handle for c in chunks]
    # Short file page stays as one chunk — no auto sub-split.
    assert "doc:io:time.sim:time-sim" in handles
    # day_start is attributed to time.sim via the running file context.
    assert "doc:io:time.sim:day-start" in handles


def test_chunker_metadata_carries_source_ref() -> None:
    chunks = _chunks_from_fixture()
    assert chunks, "fixture produced no chunks"
    for chunk in chunks:
        assert "source_ref" in chunk.metadata
        assert str(chunk.metadata["source_ref"]).startswith("https://")


def test_chunker_source_ref_override(tmp_path: Path) -> None:
    src = tmp_path / "synthetic.txt"
    src.write_text("# time.sim\n\nFake body.\n")
    chunks = chunk_io_docs(src, source_ref="https://example.invalid/custom")
    assert chunks[0].metadata["source_ref"] == "https://example.invalid/custom"


def test_empty_document_yields_no_chunks(tmp_path: Path) -> None:
    src = tmp_path / "empty.txt"
    src.write_text("")
    assert chunk_io_docs(src) == ()


def test_preface_before_first_header_is_dropped(tmp_path: Path) -> None:
    src = tmp_path / "synthetic.txt"
    src.write_text("Orphan preface with no header.\n\n# time.sim\n\nBody.\n")
    chunks = chunk_io_docs(src)
    # Only one chunk, and the preface text must not bleed into it.
    assert len(chunks) == 1
    assert "Orphan preface" not in chunks[0].text


@pytest.mark.parametrize("title", ["day\\_start", "DAY\\_START", "Day Start"])
def test_slugify_is_case_and_escape_insensitive(tmp_path: Path, title: str) -> None:
    src = tmp_path / "synthetic.txt"
    src.write_text(f"# time.sim\n\nFile page.\n\n# {title}\n\nField body.\n")
    chunks = chunk_io_docs(src)
    slugs = {c.handle.split(":")[-1] for c in chunks if c.handle != "doc:io:time.sim:time-sim"}
    assert slugs == {"day-start"}
