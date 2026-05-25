"""Unit tests for :func:`swatplus_ai.parser._base.expect_header_permissive`."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser._base import Line, ParseError, expect_header_permissive


def _line(header: str) -> Line:
    return Line(line_no=2, text=header, tokens=tuple(header.split()))


def test_exact_match_populates_idx_map_and_empty_unknowns() -> None:
    idx, unknowns = expect_header_permissive(
        _line("a b c"),
        ("a", "b", "c"),
        path=Path("dummy"),
    )
    assert idx == {"a": 0, "b": 1, "c": 2}
    assert unknowns == ()


def test_extra_column_returned_in_unknowns_with_position() -> None:
    idx, unknowns = expect_header_permissive(
        _line("a b extra c"),
        ("a", "b", "c"),
        path=Path("dummy"),
    )
    assert idx == {"a": 0, "b": 1, "c": 3}
    assert unknowns == (("extra", 2),)


def test_multiple_extra_columns_preserve_header_order() -> None:
    idx, unknowns = expect_header_permissive(
        _line("x a y b z c"),
        ("a", "b", "c"),
        path=Path("dummy"),
    )
    assert idx == {"a": 1, "b": 3, "c": 5}
    assert unknowns == (("x", 0), ("y", 2), ("z", 4))


def test_missing_required_column_raises() -> None:
    with pytest.raises(ParseError, match="missing expected column"):
        expect_header_permissive(
            _line("a c"),
            ("a", "b", "c"),
            path=Path("dummy"),
        )


def test_missing_required_column_raises_with_extras_present() -> None:
    """Extras don't satisfy a missing required column."""
    with pytest.raises(ParseError, match=r"missing expected column\(s\) \['b'\]"):
        expect_header_permissive(
            _line("a extra c"),
            ("a", "b", "c"),
            path=Path("dummy"),
        )


def test_alias_matches_canonical_name() -> None:
    """Canonical name is used in idx_map even when an alias matched."""
    idx, unknowns = expect_header_permissive(
        _line("a alt_b c"),
        ("a", "b", "c"),
        path=Path("dummy"),
        aliases={"b": ("alt_b",)},
    )
    assert idx == {"a": 0, "b": 1, "c": 2}
    assert unknowns == ()


def test_case_insensitive_match() -> None:
    idx, unknowns = expect_header_permissive(
        _line("A B C"),
        ("a", "b", "c"),
        path=Path("dummy"),
    )
    assert idx == {"a": 0, "b": 1, "c": 2}
    assert unknowns == ()


def test_column_order_in_file_preserved_via_index_map() -> None:
    """Expected order differs from actual order — idx_map reflects actual positions."""
    idx, unknowns = expect_header_permissive(
        _line("c a b"),
        ("a", "b", "c"),
        path=Path("dummy"),
    )
    assert idx == {"a": 1, "b": 2, "c": 0}
    assert unknowns == ()
