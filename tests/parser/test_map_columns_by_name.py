"""Unit tests for :func:`swatplus_ai.parser.outputs._base.map_columns_by_name`."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.diagnostics.drift import DriftRegistry
from swatplus_ai.parser.outputs._base import (
    STRICT_CORE,
    OutputParseError,
    _record_unknown_output_columns,
    map_columns_by_name,
)


def test_exact_match_maps_all() -> None:
    """Header identical to canonical — every name maps to its header index."""
    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens=("a", "b", "c"),
        canonical_fields=("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
        strict_core=(),
    )
    assert name_to_idx == {"a": 0, "b": 1, "c": 2}
    assert header_deduped == ("a", "b", "c")
    assert unknowns == ()


def test_reordered_header_still_maps() -> None:
    """Arbitrary header order — each canonical name points to the real column."""
    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens=("c", "a", "b"),
        canonical_fields=("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
        strict_core=(),
    )
    assert name_to_idx == {"a": 1, "b": 2, "c": 0}
    assert header_deduped == ("c", "a", "b")
    assert unknowns == ()


def test_missing_canonical_field_returns_minus_one() -> None:
    """Canonical name absent from header — sentinel -1, no raise, no unknown."""
    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens=("a", "c"),
        canonical_fields=("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
        strict_core=(),
    )
    assert name_to_idx == {"a": 0, "b": -1, "c": 1}
    assert header_deduped == ("a", "c")
    assert unknowns == ()


def test_unknown_header_column_reported_in_tuple() -> None:
    """Header column not declared in canonical — appears in ``unknown_columns``."""
    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens=("a", "zbar", "b", "c"),
        canonical_fields=("a", "b", "c"),
        path=Path("dummy"),
        line_no=2,
        strict_core=(),
    )
    assert name_to_idx == {"a": 0, "b": 2, "c": 3}
    assert header_deduped == ("a", "zbar", "b", "c")
    assert unknowns == (("zbar", 1),)


def test_unknown_header_column_emits_drift() -> None:
    """``_record_unknown_output_columns`` fed with the helper's output
    produces a ``DriftRecord`` with ``category="unknown_column"``."""
    _, _, unknowns = map_columns_by_name(
        header_tokens=("a", "zbar", "b", "c"),
        canonical_fields=("a", "b", "c"),
        path=Path("synthetic.txt"),
        line_no=2,
        strict_core=(),
    )
    with DriftRegistry() as reg:
        _record_unknown_output_columns(
            path=Path("synthetic.txt"),
            unknowns=unknowns,
            data_lines=["1.0 9.9 2.0 3.0"],
        )
    records = reg.all()
    assert len(records) == 1
    (rec,) = records
    assert rec.column == "zbar"
    assert rec.category == "unknown_column"
    assert rec.file == "synthetic.txt"
    assert rec.observed == "9.9"


def test_missing_strict_core_raises() -> None:
    """Header missing any ``strict_core`` name is unrecognisable — raises."""
    header = ("jday", "mon", "day", "yr", "gis_id", "name", "precip")
    # ``unit`` absent — this is the canonical SWAT+ core minus one identifier.
    with pytest.raises(OutputParseError, match="missing required core"):
        map_columns_by_name(
            header_tokens=header,
            canonical_fields=(*STRICT_CORE, "precip"),
            path=Path("dummy"),
            line_no=2,
        )


def test_duplicate_header_name_raises() -> None:
    """Header repeats a canonical name more times than canonical allows."""
    with pytest.raises(OutputParseError, match="ambiguous"):
        map_columns_by_name(
            header_tokens=("a", "nuptake", "nuptake", "b"),
            canonical_fields=("a", "nuptake", "b"),
            path=Path("dummy"),
            line_no=2,
            strict_core=(),
        )


def test_canonical_triple_null_matches_header_triple_null() -> None:
    """Legitimate canonical duplicates (``null`` x 3) dedup and map cleanly."""
    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens=("a", "null", "b", "null", "c", "null"),
        canonical_fields=("a", "null", "b", "null", "c", "null"),
        path=Path("dummy"),
        line_no=2,
        strict_core=(),
    )
    assert name_to_idx == {
        "a": 0,
        "null": 1,
        "b": 2,
        "null_2": 3,
        "c": 4,
        "null_3": 5,
    }
    assert header_deduped == ("a", "null", "b", "null_2", "c", "null_3")
    assert unknowns == ()


def test_strict_core_default_is_seven_row_identifiers() -> None:
    """Default ``strict_core`` is the seven SWAT+ row identifiers."""
    assert STRICT_CORE == ("jday", "mon", "day", "yr", "unit", "gis_id", "name")


def test_full_strict_core_plus_reordered_physicals() -> None:
    """End-to-end: all seven core ids present, physicals reordered freely."""
    header = (
        "jday", "mon", "day", "yr", "unit", "gis_id", "name",
        "puptake", "nuptake", "precip",
    )  # fmt: skip
    canonical = (
        "jday", "mon", "day", "yr", "unit", "gis_id", "name",
        "precip", "nuptake", "puptake",
    )  # fmt: skip
    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens=header,
        canonical_fields=canonical,
        path=Path("dummy"),
        line_no=2,
    )
    # Canonical "precip" is last but sits at header index 9;
    # canonical "puptake" is last-but-two but sits at header index 7.
    assert name_to_idx["precip"] == 9
    assert name_to_idx["puptake"] == 7
    assert name_to_idx["nuptake"] == 8
    assert header_deduped == header
    assert unknowns == ()
