"""Adversarial tests for the telemetry redact utility.

The redactor runs against every emitted payload, so false negatives
(leaking a real key) are much worse than false positives (redacting a
harmless long hash). Each dirty pattern gets its own test so a
regression points straight at the pattern that broke.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.telemetry.redact import REDACTED_MARKER, redact


def test_anthropic_key_is_redacted() -> None:
    dirty = "token: sk-ant-abc123def456ghi789jkl012mno"
    assert redact(dirty) == f"token: {REDACTED_MARKER}"


def test_openai_key_is_redacted() -> None:
    assert redact("sk-abcdef0123456789abcdef0123") == REDACTED_MARKER


def test_openai_hyphenated_key_caught_by_token_fallback() -> None:
    # sk-proj-... is not matched by the strict sk-[alnum]{20,} pattern,
    # but the generic token regex catches the full run because hyphens
    # are token-alphabet characters.
    assert redact("sk-proj-abc123def456ghi789jklmno") == REDACTED_MARKER


def test_email_is_redacted() -> None:
    assert redact("contact me at alice.jones@example.com please") == (
        f"contact me at {REDACTED_MARKER} please"
    )


def test_windows_path_collapsed_to_basename() -> None:
    assert redact("opened C:\\Users\\alice\\project\\file.txt") == "opened file.txt"


def test_posix_path_collapsed_to_basename() -> None:
    assert redact("reading /home/alice/project/TxtInOut/time.sim") == "reading time.sim"


def test_path_object_collapsed_to_basename() -> None:
    assert redact(Path("/home/alice/project/file.txt")) == "file.txt"


def test_long_hex_token_is_redacted() -> None:
    assert redact("hash: deadbeef1234567890cafe1234567890") == f"hash: {REDACTED_MARKER}"


def test_base64_token_is_redacted() -> None:
    assert redact("payload dGVzdGluZ3Rlc3RpbmdkYXRhY29yZWhlcmU=") == (f"payload {REDACTED_MARKER}")


def test_clean_english_passes_through() -> None:
    phrase = "This is a normal sentence explaining the SWAT+ water balance."
    assert redact(phrase) == phrase


def test_short_identifier_passes_through() -> None:
    # 10 chars — under the token-length threshold, no prefix, not an email.
    assert redact("sta001.pcp") == "sta001.pcp"


def test_long_digitless_identifier_passes_through() -> None:
    # 24+ chars but all letters + underscore — looks like a long Python
    # symbol, not a secret. Real API keys / SHA / base64 always contain
    # digits, so the token regex requires one before redacting.
    assert redact("setup.object_count_consistency") == "setup.object_count_consistency"
    assert redact("class BasinSimulationPipelineConfig:") == "class BasinSimulationPipelineConfig:"


def test_url_is_not_misread_as_posix_path() -> None:
    # Scheme-prefixed URLs must not trigger path redaction (their leading
    # ``/`` is preceded by ``:`` or another ``/``).
    url = "see https://example.com/docs/index.html for details"
    assert redact(url) == url


def test_non_string_scalars_pass_through() -> None:
    assert redact(42) == 42
    assert redact(3.14) == 3.14
    assert redact(True) is True
    assert redact(None) is None


def test_redact_walks_nested_structures() -> None:
    dirty = {
        "email": "x@y.co",
        "path": "/home/u/f.txt",
        "nested": [
            {"key": "sk-ant-abcdefghij1234567890abcdef"},
            ("leave", "alone", 12),
        ],
        "tuple": ("/tmp/session/data.csv", 7),
    }
    clean = redact(dirty)
    assert clean == {
        "email": REDACTED_MARKER,
        "path": "f.txt",
        "nested": [
            {"key": REDACTED_MARKER},
            ("leave", "alone", 12),
        ],
        "tuple": ("data.csv", 7),
    }
    # Ensure tuples are rebuilt as tuples (not lists).
    assert isinstance(clean["tuple"], tuple)
