"""Parser for ``lum.dtl`` — land-use management decision tables.

Thin wrapper over :func:`parse_decision_tables`. Each table is an
independent planting / harvest / irrigation / rotation rule keyed by
``name``. See :mod:`swatplus_ai.parser.inputs._decision_table` for the
shared grammar.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser.inputs._decision_table import DecisionTable, parse_decision_tables
from swatplus_ai.parser.models import ParsedFile


class LumDtl(ParsedFile):
    """Contents of a ``lum.dtl`` file."""

    tables: tuple[DecisionTable, ...]

    def by_name(self, name: str) -> DecisionTable | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None


def parse_lum_dtl(path: Path) -> LumDtl:
    """Parse a ``lum.dtl`` file into a :class:`LumDtl` model."""
    title, tables = parse_decision_tables(path)
    return LumDtl(source_path=path, title=title, tables=tables)
