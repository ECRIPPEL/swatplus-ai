"""Emit a JSON Schema document covering every :mod:`swatplus_ai.api.models`
view-model, to be piped through ``json2ts`` (json-schema-to-typescript).

Usage:

    python scripts/gen_ts.py > /tmp/schemas.json
    npx --prefix ui json2ts --input /tmp/schemas.json \\
        --output ui/src/lib/schemas.ts

Or the one-shot ``pnpm -C ui gen:types`` wrapper defined in
``ui/package.json``.

Design:

* We bundle every view-model under a shared ``$defs`` block so ``json2ts``
  emits a single ``schemas.ts`` file with one ``export interface`` per
  model and no inlined duplicates (``Citation`` is referenced by
  ``FindingVM`` — without shared ``$defs`` it would be copied in).
* ``by_alias=True`` makes the schema emit camelCase keys to match the UI's
  existing convention (``warmupYears``, ``readyToRun``, …).
* The root schema has ``title: "SwatplusAiApi"`` so json2ts produces a
  top-level interface we can ignore on the UI side — every meaningful
  type lives under ``$defs``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Bootstrap ``src/`` onto sys.path so ``pnpm -C ui gen:types`` works without
# requiring ``pip install -e .`` — the script is self-contained.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from pydantic.json_schema import models_json_schema  # noqa: E402

from swatplus_ai.api.models import (  # noqa: E402
    Citation,
    FindingVM,
    LanduseSlice,
    ProjectMeta,
)

_MODELS = [
    (Citation, "validation"),
    (FindingVM, "validation"),
    (LanduseSlice, "validation"),
    (ProjectMeta, "validation"),
]


def _strip_property_titles(defs: dict[str, object]) -> dict[str, object]:
    """Drop pydantic's per-field ``title`` keys from every property.

    Without this, ``json2ts`` turns every field into a named type alias
    (``export type Id = string;``) which clutters the generated file and
    collides on common field names across models (``Id`` / ``Id1`` /
    ``Name`` / ``Name1``). Properties still carry ``description`` and
    ``type``, which is all the TS interface needs.
    """
    for schema in defs.values():
        if not isinstance(schema, dict):
            continue
        props = schema.get("properties")
        if not isinstance(props, dict):
            continue
        for field_schema in props.values():
            if isinstance(field_schema, dict):
                field_schema.pop("title", None)
    return defs


def build_schema() -> dict[str, object]:
    """Merge every view-model into one JSON Schema document."""
    _, merged = models_json_schema(
        _MODELS,  # type: ignore[arg-type]
        ref_template="#/$defs/{model}",
        by_alias=True,
    )
    defs = _strip_property_titles(merged.get("$defs", {}))
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "SwatplusAiApi",
        "type": "object",
        "description": (
            "Auto-generated from src/swatplus_ai/api/models.py. "
            "Do not edit — run `pnpm -C ui gen:types` to refresh."
        ),
        "$defs": defs,
        "additionalProperties": False,
    }


def main() -> None:
    schema = build_schema()
    json.dump(schema, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
