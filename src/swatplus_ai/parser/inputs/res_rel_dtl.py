"""Parser for ``res_rel.dtl`` — reservoir / wetland release decision tables.

Thin wrapper over :func:`parse_decision_tables`. Each table encodes a
volume-/season-driven release policy keyed by ``name``. See
:mod:`swatplus_ai.parser.inputs._decision_table` for the shared grammar.
"""

from __future__ import annotations

from pathlib import Path

from swatplus_ai.parser.inputs._decision_table import DecisionTable, parse_decision_tables
from swatplus_ai.parser.models import ParsedFile


class ResRelDtl(ParsedFile):
    """Contents of a ``res_rel.dtl`` file."""

    tables: tuple[DecisionTable, ...]

    def by_name(self, name: str) -> DecisionTable | None:
        for t in self.tables:
            if t.name == name:
                return t
        return None


def parse_res_rel_dtl(path: Path) -> ResRelDtl:
    """Parse a ``res_rel.dtl`` file into a :class:`ResRelDtl` model."""
    title, tables = parse_decision_tables(path)
    return ResRelDtl(source_path=path, title=title, tables=tables)
