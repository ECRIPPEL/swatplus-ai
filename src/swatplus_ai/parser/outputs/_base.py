"""Shared reader for SWAT+ tabular annual / yearly output files.

SWAT+ output files share a repeating line layout:

* line 1 — free-text title (writer id, run timestamp, model revision);
* line 2 — whitespace-separated column header;
* line 3 — whitespace-separated unit row (shorter than the header — id /
  text columns have no unit, so the units start at the first physical
  variable);
* lines 4+ — whitespace-separated data rows, typically with right-justified
  numbers and left-justified text values.

These files are tabular time-series, not inputs: we return a
:class:`pandas.DataFrame` rather than a pydantic model.

**Header names are ground truth.** Since slice 7.3k the shared reader
maps declared columns to the actual on-disk header *by name*, via
:func:`map_columns_by_name`. The Fortran simulator rev — which is
baked into the compiled binary and can differ from the Editor rev
declared in ``file.cio`` — is free to reorder, rename, or omit
individual physical columns between revisions. As long as the seven
row-identifier columns (``jday``, ``mon``, ``day``, ``yr``, ``unit``,
``gis_id``, ``name``) are present, the parser degrades gracefully:

* canonical columns absent from the header map to ``-1`` and render as
  ``NaN`` / ``None`` in the resulting DataFrame (module was off, or the
  rev never emitted that field);
* header columns the parser doesn't know about become
  :class:`~swatplus_ai.diagnostics.drift.DriftRecord`
  ``category="unknown_column"`` entries — surfaced via the CLI drift
  footer, never raising.

Two header-contract entry points are retained for clarity:

* :func:`read_aa_output` — files whose schema is fully pinned (strict
  readers: channel / aquifer / reservoir / wetland / morph outputs).
  The canonical list includes every column the writer is known to
  emit; no module-conditional optional tail.
* :func:`read_aa_output_variable` — files with a stable physical core
  plus a module-dependent tail (``plant_cov`` / ``mgt_ops`` / ``percn``)
  that the writer emits only when the relevant module is active for
  the run. Absence of the tail is not drift.

Both paths share the same name-based machinery; the distinction is
purely descriptive of the real-world schema.

Two real-world quirks the reader has to handle:

* Repeated column names. ``channel_sd_aa`` / ``reservoir_aa`` /
  ``wetland_aa`` use the literal ``null`` three times as a separator
  between the storage, inflow and outflow blocks; ``channel_sdmorph_aa``
  repeats ``deg_btm`` and ``deg_bank``. We disambiguate in place by
  appending ``_2``, ``_3`` suffixes — on both the canonical list and
  the header — so name-based mapping sees unique labels.
* Multi-word values inside a single logical field. Basin-level averages
  report e.g. ``plant_cov = "Original Simulation"`` as two whitespace-
  separated tokens. The reader re-joins the excess tokens back into the
  configured ``text_merge_col``.

Basin-level files also sometimes truncate trailing columns (the per-HRU
``plant_cov`` / ``mgt_ops`` / ``percn`` make no sense at the basin scale
and SWAT+ omits them). Short rows are padded with ``NaN``.

**Trailing scenario metadata.** Every data row written by the SWAT+
Fortran driver ends in a 3-token scenario block — two text tokens
(``sim%description``, default ``"Original Simulation"``) and one numeric
token whose semantic is documented upstream as the current calibration
``value``. The block is not declared in the header row; the writer just
appends it verbatim to every output row, in every output file. We strip
these tokens from each data row before schema-matching so they don't
bleed into the last declared column (previously ``plant_cov`` silently
absorbed the multi-word ``"Original Simulation"`` string, masking what
should have been a NaN / real value). The stripping is governed by
:func:`strip_trailing_scenario_tokens` and is keyed off the real header
width, not the canonical count — otherwise a shorter-than-canonical
header would lose tokens when it shouldn't.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from swatplus_ai.diagnostics.drift import DriftRecord, record_drift

_TEXT_COLUMNS: frozenset[str] = frozenset({"name", "plant_cov", "mgt_ops"})

STRICT_CORE: tuple[str, ...] = (
    "jday", "mon", "day", "yr", "unit", "gis_id", "name",
)  # fmt: skip
"""The seven row-identifier columns every SWAT+ ``*_aa.txt`` writer emits.

Name-based mapping requires these to be present — without them the file
is unrecognisable as an SWAT+ output and guessing at column semantics
from physical fields alone would be unsafe. A header missing any of
these raises :class:`OutputParseError` rather than degrading silently.
"""


class OutputParseError(ValueError):
    """A SWAT+ output file failed to parse."""

    def __init__(self, path: Path, line_no: int, reason: str) -> None:
        self.path = path
        self.line_no = line_no
        self.reason = reason
        loc = f"{path}:{line_no}" if line_no > 0 else str(path)
        super().__init__(f"{loc}: {reason}")


def strip_trailing_scenario_tokens(
    tokens: Sequence[str],
    declared_header_count: int,
    *,
    expected_trailing_count: int = 3,
    path: Path,
    line_no: int,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split a data row into declared tokens and the trailing scenario block.

    The SWAT+ Fortran output writer appends a fixed-size scenario block
    (default three tokens: two for ``sim%description`` and one for the
    current calibration value) to every data row, in every output file.
    The block is *not* declared in the header row, so a naive 1:1 match
    against the declared columns mis-maps the block into the last one —
    typically ``plant_cov`` — and the real value silently disappears.

    This helper isolates the trailing block. Behaviour:

    * ``len(tokens) == declared_header_count`` — an older / synthetic
      writer that never emitted the block. Returns the row unchanged
      with an empty trailing tuple.
    * ``len(tokens) < expected_trailing_count`` — the row cannot even
      accommodate the scenario block. Raised as :class:`OutputParseError`.
    * ``expected_trailing_count <= len(tokens) < declared_header_count``
      — a short row (e.g. basin-scale output with optional tail
      legitimately omitted). The caller pads these to ``NaN``; we do not
      strip, otherwise real physical values would disappear.
    * ``len(tokens) > declared_header_count`` — the canonical case.
      Slice off the last ``expected_trailing_count`` tokens and return
      them separately.

    The trailing tuple is returned rather than discarded so future
    telemetry / validation layers can inspect it (today: ignored).
    """
    n = len(tokens)
    if n == declared_header_count:
        return tuple(tokens), ()
    if n < expected_trailing_count:
        raise OutputParseError(
            path,
            line_no,
            f"row has {n} token(s); expected at least "
            f"{expected_trailing_count} for the trailing scenario block",
        )
    if n < declared_header_count:
        return tuple(tokens), ()
    declared = tuple(tokens[:-expected_trailing_count])
    trailing = tuple(tokens[-expected_trailing_count:])
    return declared, trailing


def map_columns_by_name(
    header_tokens: Sequence[str],
    canonical_fields: Sequence[str],
    *,
    path: Path,
    line_no: int,
    strict_core: Sequence[str] = STRICT_CORE,
) -> tuple[dict[str, int], tuple[str, ...], tuple[tuple[str, int], ...]]:
    """Build a name→header-position map from the actual on-disk header.

    The canonical list declares every column the parser knows how to
    emit into the DataFrame. The actual file header declares what the
    Fortran simulator rev wrote. The two need not match in order, in
    count, or in the exact set of names; this function reconciles them
    by name.

    Returns ``(name_to_idx, header_deduped, unknown_columns)``:

    * ``name_to_idx`` — each canonical name (after duplicate-name
      deduplication via :func:`_dedupe_columns`) mapped to its
      0-based position in the deduplicated header, or ``-1`` if the
      header doesn't emit that column.
    * ``header_deduped`` — the on-disk header with repeated names
      suffixed (``null`` → ``null_2`` → ``null_3``). Downstream data-row
      parsing uses this width as the authoritative column count.
    * ``unknown_columns`` — ``(name, position)`` pairs for each header
      token whose deduplicated name is absent from ``canonical_fields``,
      in header order. Callers emit a
      :class:`~swatplus_ai.diagnostics.drift.DriftRecord` with
      ``category="unknown_column"`` per entry.

    Contract:

    * **Order-agnostic.** The ordering of ``canonical_fields`` does not
      constrain the header; only the set of declared names matters.
    * **strict_core must be present.** Every name in ``strict_core``
      must appear in ``header_tokens`` — missing identifiers are a
      file-recognition failure, not drift, so we raise. Defaults to the
      seven ``*_aa.txt`` row identifiers (:data:`STRICT_CORE`).
    * **Ambiguous duplicates raise.** A header that repeats a canonical
      name more times than canonical itself declares is ambiguous and
      raises :class:`OutputParseError` — e.g. a writer emitting
      ``nuptake`` twice when the schema expects it once. Legitimate
      canonical duplicates (``null`` x 3 in channel / reservoir / wetland
      schemas) match via the dedup machinery without raising.
    """
    header_count = Counter(header_tokens)
    canonical_count = Counter(canonical_fields)

    missing_core = [name for name in strict_core if name not in header_count]
    if missing_core:
        raise OutputParseError(
            path,
            line_no,
            f"missing required core column(s) {missing_core} in header {list(header_tokens)}",
        )

    for name, count in header_count.items():
        expected = canonical_count.get(name, 0)
        if expected > 0 and count > expected:
            raise OutputParseError(
                path,
                line_no,
                f"header contains {count} occurrence(s) of {name!r} but "
                f"canonical schema expects {expected}; ambiguous",
            )

    header_deduped = _dedupe_columns(tuple(header_tokens))
    canonical_deduped = _dedupe_columns(tuple(canonical_fields))
    header_positions = {name: i for i, name in enumerate(header_deduped)}

    name_to_idx = {name: header_positions.get(name, -1) for name in canonical_deduped}

    canonical_set = set(canonical_deduped)
    unknown_columns = tuple(
        (name, i) for i, name in enumerate(header_deduped) if name not in canonical_set
    )

    return name_to_idx, header_deduped, unknown_columns


def expect_header_with_variable_suffix(
    tokens: Sequence[str],
    core_columns: Sequence[str],
    *,
    path: Path,
    line_no: int,
) -> tuple[dict[str, int], tuple[str, ...]]:
    """Validate a SWAT+ output header against a stable core + variable suffix.

    **Deprecated internally since slice 7.3k** — retained for backward
    compatibility with any external caller that still depends on the
    old positional-prefix contract. Internal output readers go through
    :func:`map_columns_by_name`, which is order-agnostic.

    The first ``len(core_columns)`` tokens must equal ``core_columns``
    exactly, in order — any deviation (missing token, renamed column,
    reordered prefix) raises :class:`OutputParseError`. Everything after
    the core is returned as-is in ``optional_columns`` and the returned
    ``idx_map`` covers both the core names and whatever trailing tokens
    the writer happened to emit.
    """
    if len(tokens) < len(core_columns):
        raise OutputParseError(
            path,
            line_no,
            f"header too short: core schema requires {len(core_columns)} "
            f"column(s), got {len(tokens)}",
        )
    for i, expected in enumerate(core_columns):
        if tokens[i] != expected:
            raise OutputParseError(
                path,
                line_no,
                f"core header column {i}: expected {expected!r}, got {tokens[i]!r}",
            )
    idx_map: dict[str, int] = {name: i for i, name in enumerate(core_columns)}
    optional = tuple(tokens[len(core_columns) :])
    for i, name in enumerate(optional, start=len(core_columns)):
        idx_map.setdefault(name, i)
    return idx_map, optional


def read_aa_output(
    path: Path,
    *,
    expected_columns: tuple[str, ...],
    text_merge_col: str | None = None,
) -> pd.DataFrame:
    """Read a SWAT+ annual / yearly tabular output file into a DataFrame.

    Used for files whose schema is fully pinned — every column the
    writer is known to emit is declared in ``expected_columns``. Since
    slice 7.3k this matching is **by name**: reordered headers parse
    fine, canonical columns absent from the header come through
    ``NaN``, and header tokens not in ``expected_columns`` are recorded
    as ``unknown_column`` drift rather than raising.

    The title and unit row travel on ``df.attrs`` so downstream code can
    reference them without re-opening the file:

    * ``df.attrs["title"]`` — raw first line as written by SWAT+.
    * ``df.attrs["units"]`` — tuple of unit tokens, in the order they
      appear in the unit row (shorter than the column list — see module
      docstring).
    * ``df.attrs["source_path"]`` — original file path as a string.

    ``text_merge_col`` names the canonical column that absorbs excess
    tokens when a data row is wider than the header + trailing-scenario
    block — used for basin-level averages where ``plant_cov`` may carry
    multi-word values like ``"Original Simulation"``. If the named
    column is absent from the actual header, no merging is attempted.
    """
    return _read_aa_output_named(
        path,
        canonical_fields=expected_columns,
        optional_columns=(),
        text_merge_col=text_merge_col,
    )


def read_aa_output_variable(
    path: Path,
    *,
    core_columns: tuple[str, ...],
    optional_columns: tuple[str, ...] = ("plant_cov", "mgt_ops"),
    text_merge_col: str | None = None,
) -> pd.DataFrame:
    """Read a SWAT+ output file with stable core + module-conditional tail.

    Since slice 7.3k, mapping is by name rather than positional: the
    core fields, the optional tail fields (``plant_cov``, ``mgt_ops``,
    and for land-surface files also ``percn``), and anything else the
    writer actually emits are reconciled against the real on-disk
    header. The resulting DataFrame carries every core field (``NaN``
    when the rev didn't emit one) and each optional column that was
    actually present in the header — absence of an optional column
    means the DataFrame simply doesn't have that column, matching the
    legacy variable-suffix contract.

    ``optional_columns`` is the list of module-conditional columns
    whose *absence* must **not** emit drift. Anything in the header
    that is neither in ``core_columns`` nor in ``optional_columns``
    becomes an ``unknown_column`` drift record.

    ``text_merge_col`` may name a core column or an optional one — see
    :func:`read_aa_output` for details.
    """
    return _read_aa_output_named(
        path,
        canonical_fields=core_columns,
        optional_columns=optional_columns,
        text_merge_col=text_merge_col,
    )


def _read_aa_output_named(
    path: Path,
    *,
    canonical_fields: Sequence[str],
    optional_columns: Sequence[str],
    text_merge_col: str | None,
) -> pd.DataFrame:
    """Shared name-based entry point for both strict and variable-suffix readers."""
    title, header_tokens, units, data_lines, line_offset = _read_preamble(path)

    all_canonical = tuple(canonical_fields) + tuple(optional_columns)
    if text_merge_col is not None and text_merge_col not in all_canonical:
        raise OutputParseError(
            path,
            0,
            f"text_merge_col {text_merge_col!r} not in canonical fields",
        )

    name_to_idx, header_deduped, unknowns = map_columns_by_name(
        header_tokens,
        all_canonical,
        path=path,
        line_no=2,
    )
    _record_unknown_output_columns(
        path=path,
        unknowns=unknowns,
        data_lines=data_lines,
    )

    required_deduped = _dedupe_columns(tuple(canonical_fields))
    optional_present = tuple(name for name in optional_columns if name_to_idx.get(name, -1) >= 0)
    df_columns = required_deduped + optional_present

    return _build_dataframe(
        path=path,
        title=title,
        units=units,
        df_columns=df_columns,
        header_deduped=header_deduped,
        name_to_idx=name_to_idx,
        text_merge_col=text_merge_col,
        data_lines=data_lines,
        line_offset=line_offset,
    )


def _record_unknown_output_columns(
    *,
    path: Path,
    unknowns: tuple[tuple[str, int], ...],
    data_lines: Sequence[str],
) -> None:
    """Emit a ``DriftRecord(category="unknown_column")`` per extra header column.

    Mirrors the inputs-side :func:`~swatplus_ai.parser._base.record_unknown_columns`
    pattern: samples ``observed`` from the first non-empty data row at
    the unknown column's position; leaves ``source_ref`` /
    ``expected_by_fortran`` as provisional placeholders for a later
    upstream-source consultation to promote the record.

    No-op when ``unknowns`` is empty or when no
    :class:`~swatplus_ai.diagnostics.drift.DriftRegistry` is active —
    the :func:`~swatplus_ai.diagnostics.drift.record_drift` call itself
    handles the latter.
    """
    if not unknowns:
        return

    first_row_tokens: tuple[str, ...] = ()
    for raw in data_lines:
        if raw.strip():
            first_row_tokens = tuple(raw.split())
            break

    file_label = path.name
    for col_name, pos in unknowns:
        sample = first_row_tokens[pos] if pos < len(first_row_tokens) else "<no rows>"
        record_drift(
            DriftRecord(
                file=file_label,
                column=col_name,
                observed=sample,
                expected_by_fortran="<pending source consultation>",
                category="unknown_column",
                source_ref="<pending>",
            )
        )


def _read_preamble(
    path: Path,
) -> tuple[str, tuple[str, ...], tuple[str, ...], list[str], int]:
    """Split the title / header / units / data-lines of a SWAT+ output file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3:
        raise OutputParseError(
            path,
            0,
            f"file has {len(lines)} line(s); expected at least 3 (title + header + units)",
        )
    title = lines[0].rstrip()
    header_tokens = tuple(lines[1].split())
    units = tuple(lines[2].split())
    return title, header_tokens, units, lines[3:], 4


def _build_dataframe(
    *,
    path: Path,
    title: str,
    units: tuple[str, ...],
    df_columns: tuple[str, ...],
    header_deduped: tuple[str, ...],
    name_to_idx: dict[str, int],
    text_merge_col: str | None,
    data_lines: list[str],
    line_offset: int,
) -> pd.DataFrame:
    """Shared row-parsing + DataFrame construction for both header modes.

    ``df_columns`` drives the resulting DataFrame shape — each row is
    built by looking up each canonical name in ``name_to_idx`` and
    pulling the corresponding on-disk token. Canonical names whose
    ``name_to_idx`` entry is ``-1`` (not emitted by this writer rev)
    render as ``None`` / ``NaN``. ``header_deduped`` supplies the real
    number of declared columns, which drives both the trailing-scenario
    stripper and the row-padding / text-merge branches.
    """
    header_width = len(header_deduped)
    merge_idx: int | None = None
    if text_merge_col is not None:
        raw_idx = name_to_idx.get(text_merge_col, -1)
        if raw_idx >= 0:
            merge_idx = raw_idx

    rows: list[list[str | None]] = []
    for offset, raw in enumerate(data_lines):
        if not raw.strip():
            continue
        line_no = line_offset + offset
        raw_tokens = raw.split()
        stripped, _trailing = strip_trailing_scenario_tokens(
            raw_tokens, header_width, path=path, line_no=line_no
        )
        tokens = list(stripped)
        if len(tokens) == header_width:
            header_row: list[str | None] = list(tokens)
        elif len(tokens) < header_width:
            header_row = list(tokens) + [None] * (header_width - len(tokens))
        elif merge_idx is not None:
            excess = len(tokens) - header_width
            merged = " ".join(tokens[merge_idx : merge_idx + excess + 1])
            header_row = [
                *tokens[:merge_idx],
                merged,
                *tokens[merge_idx + excess + 1 :],
            ]
        else:
            raise OutputParseError(
                path,
                line_no,
                f"expected {header_width} tokens, got {len(tokens)}; "
                "no text-merge column configured for this file",
            )

        rows.append(
            [
                header_row[name_to_idx[name]] if name_to_idx[name] >= 0 else None
                for name in df_columns
            ]
        )

    df = pd.DataFrame(rows, columns=list(df_columns))

    for col in df_columns:
        if col in _TEXT_COLUMNS:
            continue
        # Stripped of any ``_N`` dedup suffix: a repeated physical column
        # (``deg_btm_2``) is still numeric, but a repeated text identifier
        # wouldn't appear in _TEXT_COLUMNS anyway, so this is defensive.
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.attrs["title"] = title
    df.attrs["units"] = units
    df.attrs["source_path"] = str(path)
    return df


def _dedupe_columns(columns: tuple[str, ...]) -> tuple[str, ...]:
    """Append ``_2``, ``_3`` suffixes to repeated names, preserving order."""
    counts: dict[str, int] = {}
    result: list[str] = []
    for name in columns:
        counts[name] = counts.get(name, 0) + 1
        result.append(name if counts[name] == 1 else f"{name}_{counts[name]}")
    return tuple(result)
