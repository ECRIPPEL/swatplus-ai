"""Contract tests for the bundled ``module1_system.md`` template."""

from __future__ import annotations

import re
from importlib.resources import files


def test_template_resource_exists_and_is_readable() -> None:
    resource = files("swatplus_ai.prompts").joinpath("module1_system.md")
    # ``importlib.resources`` returns a Traversable; ``read_text`` is the
    # authoritative loader path used by the builder itself.
    text = resource.read_text(encoding="utf-8")
    assert text, "module1_system.md loaded but contained no text"


def test_template_declares_three_placeholders() -> None:
    text = files("swatplus_ai.prompts").joinpath("module1_system.md").read_text(encoding="utf-8")
    placeholders = set(re.findall(r"\{\{([A-Z_]+)\}\}", text))
    assert placeholders == {"PROJECT_SUMMARY", "FINDINGS", "STATIC_PASSAGES"}
