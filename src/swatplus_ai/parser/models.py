"""Base pydantic types shared by every per-file parser."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ParsedFile(BaseModel):
    """Common fields present on every parsed SWAT+ file.

    ``source_path`` lets downstream code (diagnostic rules, error messages)
    refer back to the original file on disk. ``title`` preserves the raw
    first line as written by SWAT+ or its editor — often contains writer
    identification and a timestamp, useful when debugging user-reported
    issues against their real TxtInOut folder.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_path: Path
    title: str


class ConConnection(BaseModel):
    """One outflow connection from a ``*.con`` spatial-object row.

    Spatial objects (aquifers, channels, reservoirs, routing units) declare
    their downstream receivers as repeated ``(obj_typ, obj_id, hyd_typ,
    frac)`` 4-tuples after the base row fields. ``out_tot`` on the parent
    row gives the exact number of connections expected.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    obj_typ: str
    obj_id: int
    hyd_typ: str
    frac: float
