"""Unit tests for :func:`swatplus_ai.parser.outputs._base.expect_header_with_variable_suffix`."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser.outputs._base import (
    OutputParseError,
    expect_header_with_variable_suffix,
)


def test_prefix_exact_match_no_suffix() -> None:
    idx, optional = expect_header_with_variable_suffix(
        ("a", "b", "c"),
        ("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
    )
    assert idx == {"a": 0, "b": 1, "c": 2}
    assert optional == ()


def test_prefix_exact_match_with_suffix() -> None:
    idx, optional = expect_header_with_variable_suffix(
        ("a", "b", "c", "x", "y"),
        ("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
    )
    assert idx == {"a": 0, "b": 1, "c": 2, "x": 3, "y": 4}
    assert optional == ("x", "y")


def test_prefix_partial_raises() -> None:
    with pytest.raises(OutputParseError, match="header too short"):
        expect_header_with_variable_suffix(
            ("a", "b"),
            ("a", "b", "c"),
            path=Path("dummy"),
            line_no=2,
        )


def test_prefix_reordered_raises() -> None:
    with pytest.raises(OutputParseError, match="core header column 1"):
        expect_header_with_variable_suffix(
            ("a", "c", "b"),
            ("a", "b", "c"),
            path=Path("dummy"),
            line_no=2,
        )


def test_prefix_renamed_raises() -> None:
    with pytest.raises(OutputParseError, match="core header column 0"):
        expect_header_with_variable_suffix(
            ("A", "b", "c"),
            ("a", "b", "c"),
            path=Path("dummy"),
            line_no=2,
        )


def test_core_name_in_suffix_does_not_shadow_core_index() -> None:
    """Defensive: a core name repeated in the suffix keeps its core index."""
    idx, optional = expect_header_with_variable_suffix(
        ("a", "b", "c", "b"),
        ("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
    )
    assert idx["b"] == 1
    assert optional == ("b",)
