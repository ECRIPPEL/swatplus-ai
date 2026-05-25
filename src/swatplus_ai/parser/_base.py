"""Shared parsing helpers for SWAT+ TxtInOut files.

SWAT+ input files are line-oriented plain text. The first line is always a
free-text title written by the tool that produced the file. Subsequent lines
alternate between whitespace-separated column headers and matching value
rows. Some files (like print.prt) contain several header/value sections in
one file.

This module provides the minimal set of utilities every per-file parser
needs: reading lines with their original 1-based numbers preserved,
validating headers, and raising a consistent ParseError so errors surface
to the user as ``<path>:<line>: <reason>``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from swatplus_ai.diagnostics.drift import DriftRecord, record_drift


class ParseError(ValueError):
    """A SWAT+ input file failed to parse."""

    def __init__(self, path: Path, line_no: int, reason: str) -> None:
        self.path = path
        self.line_no = line_no
        self.reason = reason
        loc = f"{path}:{line_no}" if line_no > 0 else str(path)
        super().__init__(f"{loc}: {reason}")


class UnsupportedSwatPlusVersionError(RuntimeError):
    """Project declares a SWAT+ version older than the supported floor.

    Raised by :func:`swatplus_ai.parser.inputs.file_cio.check_swatplus_version`
    so the CLI and UI callers can catch this separately from a mid-parse
    structural error.
    """


@dataclass(frozen=True)
class Line:
    """A non-empty line with its original 1-based line number and tokens."""

    line_no: int
    text: str
    tokens: tuple[str, ...]


class LineReader:
    """Sequential reader over the non-empty lines of a SWAT+ file.

    Blank lines carry no grammatical meaning in SWAT+ files, so we discard
    them — but we preserve original line numbers so error messages can
    still point at the right line in the user's actual file on disk.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        lines: list[Line] = []
        for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = raw.rstrip()
            tokens = stripped.split()
            if tokens:
                lines.append(Line(line_no=i, text=stripped, tokens=tuple(tokens)))
        self._lines = lines
        self._pos = 0

    def eof(self) -> bool:
        return self._pos >= len(self._lines)

    def next(self) -> Line:
        if self._pos >= len(self._lines):
            raise ParseError(self.path, -1, "unexpected end of file")
        line = self._lines[self._pos]
        self._pos += 1
        return line


def expect_tokens(line: Line, expected: tuple[str, ...], *, path: Path) -> None:
    """Verify a header line matches the expected column names exactly.

    Comparison is case-insensitive because different SWAT+ writers vary the
    casing, but order and set of names must match. A mismatch almost always
    means a SWAT+ version we haven't taught this parser about, so we fail
    loud rather than silently mis-mapping values to fields.
    """
    got = tuple(tok.lower() for tok in line.tokens)
    want = tuple(tok.lower() for tok in expected)
    if got != want:
        raise ParseError(
            path,
            line.line_no,
            f"expected header {list(expected)}, got {list(line.tokens)}",
        )


def expect_tokens_any(
    line: Line,
    aliases: tuple[tuple[str, ...], ...],
    *,
    path: Path,
) -> int:
    """Verify a header line matches any of the accepted alias tuples.

    Different SWAT+ writers sometimes emit different column names for the
    same section at the same rev — e.g. SWAT+ Editor v3.0+ writes
    ``crop_yld`` where SWAT+ Toolbox writes ``soilout`` in ``print.prt``.
    Returns the index of the matching alias so callers can branch if needed;
    most callers just use it to accept the line.
    """
    got = tuple(tok.lower() for tok in line.tokens)
    for idx, expected in enumerate(aliases):
        if got == tuple(tok.lower() for tok in expected):
            return idx
    others = [list(a) for a in aliases[1:]]
    suffix = f" (or {others})" if others else ""
    raise ParseError(
        path,
        line.line_no,
        f"expected header {list(aliases[0])}{suffix}, got {list(line.tokens)}",
    )


def expect_header_permissive(
    line: Line,
    expected: Sequence[str],
    *,
    path: Path,
    aliases: Mapping[str, tuple[str, ...]] = {},
) -> tuple[dict[str, int], tuple[tuple[str, int], ...]]:
    """Validate expected column names are present; extra columns allowed.

    Returns ``(idx_map, unknown_columns)``:

    - ``idx_map`` maps each expected column name (canonical) to its
      0-based position in the actual header. If an alias from
      ``aliases[canonical]`` matched instead, the canonical name is
      still the key — downstream lookups stay stable.
    - ``unknown_columns`` is ``((name, position), ...)`` for every
      header token not matched by any expected name or alias, in
      header order. Callers record a :class:`DriftRecord` with
      ``category="unknown_column"`` per entry.

    Raises :class:`ParseError` if any expected column (and none of its
    aliases) is absent — missing columns are schema breakage, not drift.

    Unlike :func:`expect_tokens`, order and count are not enforced — a
    permissive parser tolerates superset headers and records the
    divergence rather than failing the whole parse. Use this for files
    where the SWAT+ Editor has evolved its column set faster than our
    baseline (e.g. ``pesticide.pes`` gaining ``pl_uptake``).
    """
    canonical_for: dict[str, str] = {}
    for name in expected:
        canonical_for[name.lower()] = name
        for alt in aliases.get(name, ()):
            canonical_for[alt.lower()] = name

    idx_map: dict[str, int] = {}
    unknowns: list[tuple[str, int]] = []
    for pos, tok in enumerate(line.tokens):
        key = tok.lower()
        canonical = canonical_for.get(key)
        if canonical is None:
            unknowns.append((tok, pos))
        elif canonical not in idx_map:
            idx_map[canonical] = pos

    missing = [name for name in expected if name not in idx_map]
    if missing:
        raise ParseError(
            path,
            line.line_no,
            f"missing expected column(s) {missing} in header {list(line.tokens)}",
        )
    return idx_map, tuple(unknowns)


def record_unknown_columns(
    unknowns: Sequence[tuple[str, int]],
    first_row: Line | None,
    *,
    file: str,
) -> None:
    """Record a ``DriftRecord(category="unknown_column")`` per extra header column.

    Samples ``observed`` from the first data row at the unknown column's
    position when available, otherwise ``"<no rows>"``. ``source_ref`` and
    ``expected_by_fortran`` are left as ``"<pending>"`` / ``"<pending source
    consultation>"``: the drift is a provisional marker until a follow-up
    slice consults upstream and promotes the record to ``spec_compliant``,
    ``tool_bug`` or ``user_invalid`` with a real reference.

    No-op when ``unknowns`` is empty or when no :class:`DriftRegistry` is
    active (the :func:`record_drift` call itself handles the latter).
    """
    for col_name, pos in unknowns:
        sample = (
            first_row.tokens[pos]
            if first_row is not None and pos < len(first_row.tokens)
            else "<no rows>"
        )
        record_drift(
            DriftRecord(
                file=file,
                column=col_name,
                observed=sample,
                expected_by_fortran="<pending source consultation>",
                category="unknown_column",
                source_ref="<pending>",
            )
        )


def parse_int(tok: str, *, path: Path, line_no: int, field: str) -> int:
    try:
        return int(tok)
    except ValueError as exc:
        raise ParseError(path, line_no, f"expected integer for {field!r}, got {tok!r}") from exc


def parse_float(tok: str, *, path: Path, line_no: int, field: str) -> float:
    try:
        return float(tok)
    except ValueError as exc:
        raise ParseError(path, line_no, f"expected float for {field!r}, got {tok!r}") from exc


def parse_int_tolerant(
    tok: str,
    *,
    path: Path,
    line_no: int,
    field: str,
) -> tuple[int, bool]:
    """Parse an integer that may have been serialized as a float by the writer.

    Returns ``(value, was_tolerant)``. ``was_tolerant`` is True when the
    token contained a decimal point but parsed to a whole-number float
    (e.g. ``"0.00000"`` → ``(0, True)``). Callers use the flag to emit
    a :class:`~swatplus_ai.diagnostics.drift.DriftRecord` noting the
    off-spec serialization — SWAT+ Editor < v3.1.0 wrote
    ``parameters.bsn.day_lag_max`` this way per its own changelog, and
    Fortran list-directed reads accept it silently.

    Anything with a non-zero fractional component or non-numeric garbage
    still raises :class:`ParseError` so genuinely bogus values surface.
    """
    try:
        return int(tok), False
    except ValueError:
        pass
    try:
        f = float(tok)
    except ValueError as exc:
        raise ParseError(path, line_no, f"expected integer for {field!r}, got {tok!r}") from exc
    if f.is_integer():
        return int(f), True
    raise ParseError(path, line_no, f"expected integer for {field!r}, got {tok!r}")


def parse_yn(tok: str, *, path: Path, line_no: int, field: str) -> bool:
    t = tok.strip().lower()
    if t == "y":
        return True
    if t == "n":
        return False
    raise ParseError(path, line_no, f"expected 'y' or 'n' for {field!r}, got {tok!r}")


def parse_nullable_str(tok: str) -> str | None:
    """SWAT+ writes the literal 'null' (any case) for unused file slots."""
    return None if tok.strip().lower() == "null" else tok


def parse_nullable_float(tok: str, *, path: Path, line_no: int, field: str) -> float | None:
    """Parse a float column that SWAT+ editor v3.0+ may write as literal ``null``.

    Real-world example: ``parameters.bsn`` rev.61.0.1 writes ``null`` for
    ``lin_sed`` / ``exp_sed`` when the user hasn't customised the sediment
    model. Falls back to :func:`parse_float` for anything else so a genuinely
    bogus value still raises a specific :class:`ParseError`.
    """
    if tok.strip().lower() == "null":
        return None
    return parse_float(tok, path=path, line_no=line_no, field=field)


_ModelT = TypeVar("_ModelT", bound=BaseModel)


def validate_or_raise(
    model_cls: type[_ModelT],
    data: dict[str, Any],
    *,
    path: Path,
    line_no: int,
) -> _ModelT:
    """Construct ``model_cls(**data)``, wrapping ValidationError as ParseError.

    Pydantic's default ``ValidationError`` string is multi-line and never
    names the file it came from. Wrapping it as :class:`ParseError` pins
    the offending file and line, so users (and the telemetry ``parse_error``
    event emitted from :mod:`swatplus_ai.parser.txtinout`) see a single-line
    ``<path>:<line>: <reason>`` instead of a bare
    ``2 validation errors for TimeSim``.
    """
    try:
        return model_cls(**data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ParseError(path, line_no, details) from exc


def parse_int_row(line: Line, fields: tuple[str, ...], *, path: Path) -> dict[str, int]:
    """Parse a whitespace-separated row of integers into a {field: value} dict."""
    if len(line.tokens) != len(fields):
        raise ParseError(
            path,
            line.line_no,
            f"expected {len(fields)} integer values, got {len(line.tokens)}",
        )
    return {
        name: parse_int(tok, path=path, line_no=line.line_no, field=name)
        for name, tok in zip(fields, line.tokens, strict=True)
    }


def parse_yn_row(line: Line, fields: tuple[str, ...], *, path: Path) -> dict[str, bool]:
    """Parse a whitespace-separated row of y/n flags into a {field: bool} dict."""
    if len(line.tokens) != len(fields):
        raise ParseError(
            path,
            line.line_no,
            f"expected {len(fields)} y/n values, got {len(line.tokens)}",
        )
    return {
        name: parse_yn(tok, path=path, line_no=line.line_no, field=name)
        for name, tok in zip(fields, line.tokens, strict=True)
    }
