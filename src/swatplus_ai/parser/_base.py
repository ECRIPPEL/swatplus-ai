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

from dataclasses import dataclass
from pathlib import Path


class ParseError(ValueError):
    """A SWAT+ input file failed to parse."""

    def __init__(self, path: Path, line_no: int, reason: str) -> None:
        self.path = path
        self.line_no = line_no
        self.reason = reason
        loc = f"{path}:{line_no}" if line_no > 0 else str(path)
        super().__init__(f"{loc}: {reason}")


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


def parse_int(tok: str, *, path: Path, line_no: int, field: str) -> int:
    try:
        return int(tok)
    except ValueError as exc:
        raise ParseError(path, line_no, f"expected integer for {field!r}, got {tok!r}") from exc


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
