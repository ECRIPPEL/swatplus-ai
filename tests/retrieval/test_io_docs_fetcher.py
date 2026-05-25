"""Cache + network behaviour for the I/O docs fetcher.

All tests monkeypatch ``httpx.get`` at the module boundary — we never
hit the real gitbook. The fixture payload is a tiny fake dump whose
only job is to be hashable and writable; the chunker has its own
fixture (``io_docs_excerpt.txt``) for structural tests.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from swatplus_ai.retrieval.sources import io_docs
from swatplus_ai.retrieval.sources.io_docs import (
    IO_DOCS_URL,
    IODocsFetchError,
    fetch_io_docs,
)

_PAYLOAD = b"# time.sim\n\nFake dump for tests.\n"


class _GetRecorder:
    """Monkeypatch target: records every ``httpx.get`` call and replies."""

    def __init__(self, response_factory: Any) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._response_factory = response_factory

    def __call__(self, url: str, **kwargs: Any) -> httpx.Response:
        self.calls.append((url, kwargs))
        return self._response_factory()


def _ok_response() -> httpx.Response:
    return httpx.Response(
        200,
        content=_PAYLOAD,
        request=httpx.Request("GET", IO_DOCS_URL),
    )


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _GetRecorder:
    rec = _GetRecorder(_ok_response)
    monkeypatch.setattr(io_docs.httpx, "get", rec)
    return rec


def test_fetcher_downloads_and_caches(tmp_path: Path, recorder: _GetRecorder) -> None:
    first = fetch_io_docs(tmp_path)
    second = fetch_io_docs(tmp_path)

    assert first == tmp_path / "llms-full.txt"
    assert first.read_bytes() == _PAYLOAD
    assert second == first
    assert len(recorder.calls) == 1, "second call should hit the cache"

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    expected_sha = hashlib.sha256(_PAYLOAD).hexdigest()
    assert manifest["sha256"] == expected_sha
    assert manifest["url"] == IO_DOCS_URL
    assert manifest["size_bytes"] == len(_PAYLOAD)
    assert manifest["fetched_at"].endswith("Z")


def test_fetcher_refetches_on_force(tmp_path: Path, recorder: _GetRecorder) -> None:
    fetch_io_docs(tmp_path)
    fetch_io_docs(tmp_path, force=True)
    assert len(recorder.calls) == 2


def test_fetcher_refetches_on_sha_mismatch(tmp_path: Path, recorder: _GetRecorder) -> None:
    fetch_io_docs(tmp_path)
    # Corrupt the cached corpus so its sha no longer matches the manifest.
    (tmp_path / "llms-full.txt").write_bytes(b"tampered")
    fetch_io_docs(tmp_path)
    assert len(recorder.calls) == 2
    assert (tmp_path / "llms-full.txt").read_bytes() == _PAYLOAD


def test_fetcher_raises_on_network_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(io_docs.httpx, "get", boom)
    with pytest.raises(IODocsFetchError) as exc:
        fetch_io_docs(tmp_path)
    assert IO_DOCS_URL in str(exc.value)


def test_fetcher_raises_on_http_error_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def five_hundred(url: str, **kwargs: Any) -> httpx.Response:
        return httpx.Response(500, content=b"server boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(io_docs.httpx, "get", five_hundred)
    with pytest.raises(IODocsFetchError):
        fetch_io_docs(tmp_path)


def test_fetcher_creates_cache_dir_when_missing(tmp_path: Path, recorder: _GetRecorder) -> None:
    nested = tmp_path / "does" / "not" / "exist"
    result = fetch_io_docs(nested)
    assert result.is_file()
    assert (nested / "manifest.json").is_file()
