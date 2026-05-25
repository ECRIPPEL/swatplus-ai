"""HTTP API layer (UI-facing view-models + adapters + FastAPI server).

The ``api`` package is the translation boundary between the parser/rule
domain (snake_case Pydantic models shaped around SWAT+ input files) and
the web UI (camelCase TypeScript interfaces shaped around user-visible
concepts). Nothing in the domain imports from ``api``; the dependency
points one way only.

Naming convention: view-models live in :mod:`.models` and are named the
same as the TypeScript interfaces they produce (``ProjectMeta``,
``FindingVM``, ``LanduseSlice``, ``Citation``) — *never* the same as a
domain class, so a reader never has to guess which layer an import
belongs to. Adapters live in :mod:`.adapters` as pure functions
(``to_project_meta``, ``to_finding_vm``, ``to_landuse_slices``).
"""

from __future__ import annotations

from swatplus_ai.api.adapters import to_finding_vm, to_landuse_slices, to_project_meta
from swatplus_ai.api.models import Citation, FindingVM, LanduseSlice, ProjectMeta

__all__ = [
    "Citation",
    "FindingVM",
    "LanduseSlice",
    "ProjectMeta",
    "to_finding_vm",
    "to_landuse_slices",
    "to_project_meta",
]
