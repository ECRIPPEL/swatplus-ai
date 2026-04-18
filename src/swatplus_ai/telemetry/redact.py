"""Pure redaction utility for telemetry event payloads.

Logs are written to disk and meant to be shareable by the user as-is for
bug reports — no secondary scrub step. :func:`redact` walks an arbitrary
Python object and rewrites anything that looks like a secret, absolute
path, email, or long opaque token. It is intentionally conservative:
false positives (redacting a harmless hash) are fine, false negatives
(leaking a real API key) are not.

Patterns, applied to every string in order:

1. Anthropic-style keys (``sk-ant-…``) and OpenAI-style keys (``sk-…``)
   → ``<REDACTED>``.
2. Email addresses → ``<REDACTED>``.
3. Absolute paths (Windows ``C:\\…`` or POSIX ``/foo/bar/…``) → basename.
4. Long opaque hex / base64 tokens (≥24 chars, word-bounded) →
   ``<REDACTED>``. Runs last so it can't swallow basenames or
   path-internal components that have already been rewritten.

Non-string scalars (``int``, ``float``, ``bool``, ``None``) pass through
unchanged; :class:`pathlib.Path` objects are shortened to their basename
string; ``dict`` / ``list`` / ``tuple`` are recursed and rebuilt.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REDACTED_MARKER = "<REDACTED>"

_ANTHROPIC_KEY = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")
_OPENAI_KEY = re.compile(r"sk-[A-Za-z0-9]{20,}")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Windows: drive letter + separator + non-space run. Stops at whitespace or
# quote. The lookbehind excludes URL schemes like ``https://…``, where the
# ``s:`` would otherwise look like a drive letter.
_WIN_PATH = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\s\"']*")
# POSIX: leading slash not preceded by an identifier char (so URLs like
# ``https://…`` and relative paths like ``a/b/c`` don't match), then at
# least one ``segment/`` group, then a final segment.
_POSIX_PATH = re.compile(r"(?<![A-Za-z0-9._/])/(?:[^\s/\"']+/)+[^\s/\"']+")
# Hex/base64 run of 24+ chars, word-bounded against the same alphabet so
# we don't bite off a fragment of a longer identifier.
_TOKEN = re.compile(r"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/=_-]{24,}(?![A-Za-z0-9+/=_-])")


def _path_to_basename(match: re.Match[str]) -> str:
    # pathlib's .name is OS-dependent (a POSIX Path won't split backslashes),
    # so split on both separators manually to stay cross-platform.
    raw = match.group(0).rstrip("\\/")
    parts = [p for p in re.split(r"[\\/]", raw) if p]
    return parts[-1] if parts else raw


def _redact_string(value: str) -> str:
    value = _ANTHROPIC_KEY.sub(REDACTED_MARKER, value)
    value = _OPENAI_KEY.sub(REDACTED_MARKER, value)
    value = _EMAIL.sub(REDACTED_MARKER, value)
    value = _WIN_PATH.sub(_path_to_basename, value)
    value = _POSIX_PATH.sub(_path_to_basename, value)
    value = _TOKEN.sub(REDACTED_MARKER, value)
    return value


def redact(obj: Any) -> Any:
    """Return a deep copy of ``obj`` with secret-shaped strings scrubbed."""
    if isinstance(obj, str):
        return _redact_string(obj)
    if isinstance(obj, Path):
        return obj.name
    if isinstance(obj, dict):
        return {k: redact(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(redact(v) for v in obj)
    return obj


__all__ = ["REDACTED_MARKER", "redact"]
