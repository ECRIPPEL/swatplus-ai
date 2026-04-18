"""Tests for :mod:`swatplus_ai.prompts.formatter`."""

from __future__ import annotations

from swatplus_ai.diagnostics.finding import Finding
from swatplus_ai.prompts.builder import StaticPassage
from swatplus_ai.prompts.formatter import (
    Citation,
    FormattedResponse,
    collect_handles,
    format_module1_response,
)


def _finding(rule_id: str, *references: str) -> Finding:
    return Finding(
        id=rule_id,
        severity="error",
        location=None,
        evidence={},
        rule_ref=rule_id,
        message="x",
        references=references,
    )


def _passage(id_: str) -> StaticPassage:
    return StaticPassage(id=id_, title="t", body="b", source="s")


# ---------------------------------------------------------------------------
# format_module1_response
# ---------------------------------------------------------------------------


def test_empty_text_returns_empty_formatted_response() -> None:
    resp = format_module1_response("", frozenset())
    assert resp.text == ""
    assert resp.citations == ()
    assert resp.unknown_citations == ()
    assert resp.has_unknown_citations is False


def test_text_without_marker_is_preserved_verbatim() -> None:
    raw = "Plain prose, no citations here. Newlines\nand punctuation.!?"
    resp = format_module1_response(raw, frozenset({"anything"}))
    assert resp.text == raw
    assert resp.citations == ()
    assert resp.unknown_citations == ()
    assert resp.has_unknown_citations is False


def test_single_known_citation_matched() -> None:
    raw = "See [doc:swatplus_io_spec] for details."
    resp = format_module1_response(raw, {"swatplus_io_spec"})
    assert len(resp.citations) == 1
    c = resp.citations[0]
    assert c.handle == "swatplus_io_spec"
    assert c.marker == "[doc:swatplus_io_spec]"
    assert raw[c.start : c.end] == c.marker
    assert resp.unknown_citations == ()
    assert resp.has_unknown_citations is False


def test_multiple_known_citations_preserve_document_order() -> None:
    raw = "First [doc:alpha] then [doc:beta] finally [doc:gamma]."
    resp = format_module1_response(raw, {"alpha", "beta", "gamma"})
    assert tuple(c.handle for c in resp.citations) == ("alpha", "beta", "gamma")
    assert resp.unknown_citations == ()


def test_same_known_handle_cited_twice_keeps_both_no_unknown() -> None:
    raw = "Cite [doc:alpha] once and [doc:alpha] again."
    resp = format_module1_response(raw, {"alpha"})
    assert len(resp.citations) == 2
    assert tuple(c.handle for c in resp.citations) == ("alpha", "alpha")
    # Distinct positions.
    assert resp.citations[0].start != resp.citations[1].start
    assert resp.unknown_citations == ()


def test_single_unknown_handle_flagged() -> None:
    raw = "See [doc:foo]."
    resp = format_module1_response(raw, frozenset())
    assert len(resp.citations) == 1
    assert resp.citations[0].handle == "foo"
    assert resp.unknown_citations == ("foo",)
    assert resp.has_unknown_citations is True


def test_unknown_handle_cited_three_times_dedups_but_keeps_all_citations() -> None:
    raw = "[doc:foo] ... [doc:foo] ... [doc:foo]"
    resp = format_module1_response(raw, frozenset())
    assert len(resp.citations) == 3
    assert all(c.handle == "foo" for c in resp.citations)
    assert resp.unknown_citations == ("foo",)


def test_mix_of_known_and_unknown_handles_order_pinned() -> None:
    raw = "[doc:k1] [doc:bad1] [doc:k2] [doc:bad2] [doc:bad1] [doc:k1]"
    resp = format_module1_response(raw, {"k1", "k2"})
    assert tuple(c.handle for c in resp.citations) == (
        "k1",
        "bad1",
        "k2",
        "bad2",
        "bad1",
        "k1",
    )
    # First-appearance order, deduped — bad1 appears twice in citations
    # but only once in unknown_citations, and before bad2.
    assert resp.unknown_citations == ("bad1", "bad2")
    assert resp.has_unknown_citations is True


def test_permissive_handle_accepts_digits_underscores_dots_hyphens() -> None:
    raw = "A [doc:plunge_2024] B [doc:swatplus-editor-check] C [doc:moriasi.2015]"
    handles = {"plunge_2024", "swatplus-editor-check", "moriasi.2015"}
    resp = format_module1_response(raw, handles)
    assert tuple(c.handle for c in resp.citations) == (
        "plunge_2024",
        "swatplus-editor-check",
        "moriasi.2015",
    )
    assert resp.unknown_citations == ()


def test_handles_are_case_sensitive() -> None:
    raw = "See [doc:Foo] and [doc:foo]."
    resp = format_module1_response(raw, {"foo"})
    assert tuple(c.handle for c in resp.citations) == ("Foo", "foo")
    # "Foo" is unknown even though a case-insensitive match exists.
    assert resp.unknown_citations == ("Foo",)


def test_citation_position_invariant_over_many_citations() -> None:
    raw = (
        "Lorem [doc:alpha] ipsum dolor [doc:beta]. Multi-line\n"
        "continuation cites [doc:gamma] again, then [doc:alpha]\n"
        "closes with [doc:delta]."
    )
    resp = format_module1_response(raw, {"alpha", "beta", "gamma", "delta"})
    assert len(resp.citations) == 5
    # The contract pin: positions are exact into the raw text.
    for c in resp.citations:
        assert raw[c.start : c.end] == c.marker, (
            f"position mismatch for {c.handle!r}: "
            f"raw[{c.start}:{c.end}]={raw[c.start : c.end]!r} vs marker={c.marker!r}"
        )


def test_raw_text_roundtrips_byte_for_byte() -> None:
    raw = "  leading spaces\nand [doc:alpha] mid-line, trailing\n\n"
    resp = format_module1_response(raw, {"alpha"})
    assert resp.text == raw  # Never mutated — no trim, no normalize.


def test_has_unknown_citations_property_reflects_tuple() -> None:
    known = format_module1_response("[doc:alpha]", {"alpha"})
    unknown = format_module1_response("[doc:alpha]", frozenset())
    assert known.has_unknown_citations is False
    assert unknown.has_unknown_citations is True


def test_bracket_edge_cases_never_match() -> None:
    # Empty handle, missing close bracket, wrong-case prefix: none of
    # these should produce a citation.
    raw = "noise [doc:] and [doc:foo and [DOC:foo] and [Doc:foo]"
    resp = format_module1_response(raw, {"foo"})
    assert resp.citations == ()
    assert resp.unknown_citations == ()


def test_citation_is_frozen_and_typed() -> None:
    c = Citation(handle="alpha", start=0, end=11, marker="[doc:alpha]")
    assert c.model_config.get("frozen") is True
    # Round-trip through FormattedResponse keeps it frozen too.
    resp = FormattedResponse(text="[doc:alpha]", citations=(c,), unknown_citations=())
    assert resp.citations[0] is c


# ---------------------------------------------------------------------------
# collect_handles
# ---------------------------------------------------------------------------


def test_collect_handles_empty_inputs_return_empty_frozenset() -> None:
    assert collect_handles([], None) == frozenset()
    assert collect_handles([], []) == frozenset()
    # Both paths yield the same empty frozenset.
    assert collect_handles([], None) == collect_handles([], [])


def test_collect_handles_return_type_is_frozenset() -> None:
    result = collect_handles([_finding("r.x", "alpha")], [_passage("beta")])
    assert isinstance(result, frozenset)


def test_collect_handles_findings_only() -> None:
    findings = [
        _finding("r.a", "alpha", "beta"),
        _finding("r.b", "beta", "gamma"),
        _finding("r.c"),  # no references
    ]
    assert collect_handles(findings) == frozenset({"alpha", "beta", "gamma"})


def test_collect_handles_passages_only() -> None:
    assert collect_handles([], [_passage("alpha"), _passage("beta")]) == frozenset(
        {"alpha", "beta"}
    )


def test_collect_handles_union_of_findings_and_passages() -> None:
    findings = [_finding("r.a", "alpha", "shared")]
    passages = [_passage("beta"), _passage("shared")]
    assert collect_handles(findings, passages) == frozenset({"alpha", "beta", "shared"})
