"""Unit tests for :func:`strip_trailing_scenario_tokens`.

The Fortran output writer appends a fixed trailing scenario block
(default three tokens: ``sim%description`` plus a numeric value) to
every data row. The stripper isolates this block from the declared
tokens so downstream schema-matching does not mis-map the block into
the last declared column.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.parser.outputs._base import (
    OutputParseError,
    strip_trailing_scenario_tokens,
)

_DUMMY_PATH = Path("dummy.txt")


def test_strip_standard_trailing() -> None:
    """N declared + 3 trailing tokens -> (N, 3) split."""
    tokens = ["365", "12", "31", "basin", "1.25", "0.4", "Original", "Simulation", "0.000"]
    declared, trailing = strip_trailing_scenario_tokens(
        tokens, declared_header_count=6, path=_DUMMY_PATH, line_no=4
    )
    assert declared == ("365", "12", "31", "basin", "1.25", "0.4")
    assert trailing == ("Original", "Simulation", "0.000")


def test_strip_no_trailing_when_exact() -> None:
    """Row with exactly N tokens passes through untouched (older writer)."""
    tokens = ["365", "12", "31", "basin", "1.25", "0.4"]
    declared, trailing = strip_trailing_scenario_tokens(
        tokens, declared_header_count=6, path=_DUMMY_PATH, line_no=4
    )
    assert declared == tuple(tokens)
    assert trailing == ()


def test_strip_insufficient_tokens_raises() -> None:
    """A row narrower than the trailing block cannot be split — raise loudly."""
    tokens = ["a", "b"]
    with pytest.raises(OutputParseError, match="expected at least 3"):
        strip_trailing_scenario_tokens(tokens, declared_header_count=6, path=_DUMMY_PATH, line_no=4)


def test_strip_custom_count() -> None:
    """``expected_trailing_count`` overrides the default slice size."""
    tokens = ["365", "12", "basin", "1.25", "Original", "0.000"]
    declared, trailing = strip_trailing_scenario_tokens(
        tokens,
        declared_header_count=4,
        expected_trailing_count=2,
        path=_DUMMY_PATH,
        line_no=4,
    )
    assert declared == ("365", "12", "basin", "1.25")
    assert trailing == ("Original", "0.000")


def test_strip_preserves_token_order() -> None:
    """Declared tokens keep their on-disk order; trailing block order preserved too."""
    tokens = ["a", "b", "c", "d", "e", "x", "y", "z"]
    declared, trailing = strip_trailing_scenario_tokens(
        tokens, declared_header_count=5, path=_DUMMY_PATH, line_no=4
    )
    assert declared == ("a", "b", "c", "d", "e")
    assert trailing == ("x", "y", "z")


def test_strip_short_row_not_stripped() -> None:
    """A row shorter than declared but >= trailing count must not be sliced.

    Basin-level outputs legitimately truncate optional columns (e.g.
    ``plant_cov`` / ``mgt_ops``) when the writer has nothing to report.
    Stripping the trailing block here would eat real physical data.
    """
    tokens = ["365", "12", "31", "basin"]
    declared, trailing = strip_trailing_scenario_tokens(
        tokens, declared_header_count=6, path=_DUMMY_PATH, line_no=4
    )
    assert declared == tuple(tokens)
    assert trailing == ()
