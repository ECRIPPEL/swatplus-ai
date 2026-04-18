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
:class:`pandas.DataFrame` rather than a pydantic model. Header names are
validated against an explicit per-file schema so a mid-release SWAT+
column change fails loudly instead of silently producing mis-aligned
columns.

Two real-world quirks the reader has to handle:

* Repeated column names. ``channel_sd_aa`` / ``reservoir_aa`` /
  ``wetland_aa`` use the literal ``null`` three times as a separator
  between the storage, inflow and outflow blocks; ``channel_sdmorph_aa``
  repeats ``deg_btm`` and ``deg_bank``. We disambiguate in place by
  appending ``_2``, ``_3`` suffixes so the resulting DataFrame has
  unique column labels.
* Multi-word values inside a single logical field. Basin-level averages
  report e.g. ``plant_cov = "Original Simulation"`` as two whitespace-
  separated tokens. The reader re-joins the excess tokens back into the
  configured ``text_merge_col``.

Basin-level files also sometimes truncate trailing columns (the per-HRU
``plant_cov`` / ``mgt_ops`` / ``percn`` make no sense at the basin scale
and SWAT+ omits them). Short rows are padded with ``NaN``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

_TEXT_COLUMNS: frozenset[str] = frozenset({"name", "plant_cov", "mgt_ops"})


class OutputParseError(ValueError):
    """A SWAT+ output file failed to parse."""

    def __init__(self, path: Path, line_no: int, reason: str) -> None:
        self.path = path
        self.line_no = line_no
        self.reason = reason
        loc = f"{path}:{line_no}" if line_no > 0 else str(path)
        super().__init__(f"{loc}: {reason}")


def read_aa_output(
    path: Path,
    *,
    expected_columns: tuple[str, ...],
    text_merge_col: str | None = None,
) -> pd.DataFrame:
    """Read a SWAT+ annual / yearly tabular output file into a DataFrame.

    The title and unit row travel on ``df.attrs`` so downstream code can
    reference them without re-opening the file:

    * ``df.attrs["title"]`` — raw first line as written by SWAT+.
    * ``df.attrs["units"]`` — tuple of unit tokens, in the order they
      appear in the unit row (shorter than the column list — see module
      docstring).
    * ``df.attrs["source_path"]`` — original file path as a string.

    ``text_merge_col`` is the column that absorbs excess tokens when a
    data line is wider than the schema — used for basin-level averages
    where ``plant_cov`` carries values like ``"Original Simulation"``.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3:
        raise OutputParseError(
            path,
            0,
            f"file has {len(lines)} line(s); expected at least 3 (title + header + units)",
        )

    title = lines[0].rstrip()
    header_line = lines[1]
    units_line = lines[2]

    got = tuple(header_line.split())
    if got != expected_columns:
        raise OutputParseError(
            path,
            2,
            f"expected header {list(expected_columns)}, got {list(got)}",
        )

    if text_merge_col is not None and text_merge_col not in expected_columns:
        raise OutputParseError(
            path,
            0,
            f"text_merge_col {text_merge_col!r} not in expected_columns",
        )

    units = tuple(units_line.split())
    final_columns = _dedupe_columns(expected_columns)
    ncols = len(expected_columns)
    merge_idx = expected_columns.index(text_merge_col) if text_merge_col else None

    rows: list[list[str | None]] = []
    for offset, raw in enumerate(lines[3:]):
        if not raw.strip():
            continue
        line_no = 4 + offset
        tokens = raw.split()
        if len(tokens) == ncols:
            rows.append(list(tokens))
        elif len(tokens) < ncols:
            padded: list[str | None] = list(tokens) + [None] * (ncols - len(tokens))
            rows.append(padded)
        elif merge_idx is not None:
            excess = len(tokens) - ncols
            merged = " ".join(tokens[merge_idx : merge_idx + excess + 1])
            rebuilt: list[str | None] = [
                *tokens[:merge_idx],
                merged,
                *tokens[merge_idx + excess + 1 :],
            ]
            rows.append(rebuilt)
        else:
            raise OutputParseError(
                path,
                line_no,
                f"expected {ncols} tokens, got {len(tokens)}; "
                "no text-merge column configured for this file",
            )

    df = pd.DataFrame(rows, columns=list(final_columns))

    for col, original in zip(final_columns, expected_columns, strict=True):
        if original in _TEXT_COLUMNS:
            continue
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
