"""Smoke test for :mod:`scripts.gen_ts`.

This doesn't run ``json2ts`` (that's a node-side concern for the
``pnpm -C ui gen:types`` workflow). We just pin that the emitted JSON
Schema is well-formed, contains every view-model under ``$defs``, and
carries camelCase property keys — the invariants json2ts relies on.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "gen_ts.py"


def test_gen_ts_emits_every_view_model() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=True,
    )
    schema = json.loads(result.stdout)

    assert schema["$schema"].startswith("http://json-schema.org/")
    defs = schema["$defs"]
    assert set(defs.keys()) == {"Citation", "FindingVM", "LanduseSlice", "ProjectMeta"}


def test_gen_ts_emits_camel_case_properties() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=True,
    )
    schema = json.loads(result.stdout)

    project_props = schema["$defs"]["ProjectMeta"]["properties"]
    assert "warmupYears" in project_props
    assert "outletLat" in project_props
    assert "readyToRun" in project_props
    assert "warmup_years" not in project_props

    landuse_props = schema["$defs"]["LanduseSlice"]["properties"]
    assert "className" in landuse_props
    assert "areaKm2" in landuse_props


def test_gen_ts_properties_have_no_titles() -> None:
    """json2ts turns property ``title`` values into noisy type aliases;
    :func:`scripts.gen_ts._strip_property_titles` removes them. Guard
    that stripping so a future pydantic version re-adding titles by
    default is caught here rather than in a generated TS diff."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=True,
    )
    schema = json.loads(result.stdout)

    for name, def_ in schema["$defs"].items():
        for prop_name, prop in def_.get("properties", {}).items():
            assert "title" not in prop, (
                f"{name}.{prop_name} leaked a 'title' — would clutter schemas.ts"
            )
