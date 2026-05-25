"""Fetch and cache the SWAT+ I/O specification (``llms-full.txt``).

The gitbook at ``https://swatplus.gitbook.io/io-docs/`` is the canonical
authority for SWAT+ input/output file semantics (per the
``project_upstream_as_truth`` principle). The gitbook publishes a flat
LLM-oriented dump at ``/llms-full.txt`` that concatenates every page
with preserved markdown headers — that dump is what the retrieval layer
ingests.

This module is intentionally minimal: one function
(:func:`fetch_io_docs`) that downloads the dump on first call, caches
it to disk alongside a manifest, and short-circuits on subsequent calls
when the cache is valid. No parsing happens here — that's
:mod:`swatplus_ai.retrieval.chunking.io_spec`.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

import httpx

IO_DOCS_URL: Final = "https://swatplus.gitbook.io/io-docs/llms-full.txt"
_CORPUS_FILENAME: Final = "llms-full.txt"
_MANIFEST_FILENAME: Final = "manifest.json"
_FETCH_TIMEOUT_SECONDS: Final = 30.0


class IODocsFetchError(RuntimeError):
    """Raised when the I/O docs dump cannot be fetched from the gitbook.

    The retrieval layer is fail-graceful by contract — a network error
    surfaces as this exception so callers can swap to an empty result
    instead of inventing a passage. Never caught inside this module;
    always re-raised with context.
    """


def fetch_io_docs(cache_dir: Path, *, force: bool = False) -> Path:
    """Download the SWAT+ I/O spec dump into ``cache_dir``.

    Returns the path of the cached corpus file. On subsequent calls,
    the file on disk is re-read, its SHA-256 is recomputed, and the
    cached copy is reused when it still matches the manifest. A
    mismatch (corrupt / truncated cache) triggers an automatic refetch
    so callers never silently index partial content.

    :param cache_dir: Directory that will hold ``llms-full.txt`` and
        ``manifest.json``. Created if missing.
    :param force: When ``True``, always refetch and overwrite the cache.
    :raises IODocsFetchError: Wraps any ``httpx`` transport error or
        non-2xx response.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    corpus_path = cache_dir / _CORPUS_FILENAME
    manifest_path = cache_dir / _MANIFEST_FILENAME

    if not force and _cache_is_valid(corpus_path, manifest_path):
        return corpus_path

    payload = _download(IO_DOCS_URL)
    corpus_path.write_bytes(payload)
    manifest_path.write_text(
        json.dumps(_build_manifest(payload, IO_DOCS_URL), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return corpus_path


def _cache_is_valid(corpus_path: Path, manifest_path: Path) -> bool:
    if not corpus_path.is_file() or not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected_sha = manifest.get("sha256")
    if not isinstance(expected_sha, str):
        return False
    actual_sha = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    return actual_sha == expected_sha


def _download(url: str) -> bytes:
    try:
        response = httpx.get(url, timeout=_FETCH_TIMEOUT_SECONDS, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise IODocsFetchError(f"failed to fetch {url}: {exc}") from exc
    return response.content


def _build_manifest(payload: bytes, url: str) -> dict[str, str | int]:
    return {
        "url": url,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
