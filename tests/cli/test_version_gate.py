"""CLI-level regression for the SWAT+ rev.61 floor enforced in
:func:`swatplus_ai.parser.inputs.file_cio.check_swatplus_version`.

A rev.60.x project must exit the ``check`` command with a non-zero code
and an actionable upgrade message — not crash deep inside a parser with
a header-mismatch error that doesn't tell the user to upgrade.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from swatplus_ai.cli import app as root_app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def rev60_project(tmp_path: Path) -> Path:
    """Copy the committed minimal fixture and rewrite ``file.cio`` to rev.60."""
    project = tmp_path / "txtinout"
    shutil.copytree(FIXTURES_DIR / "txtinout_minimal", project)
    cio = project / "file.cio"
    body = cio.read_text(encoding="utf-8").split("\n", 1)[1]
    cio.write_text(
        "file.cio: written by SWAT+ editor v2.1.3 on 2022-11-10 for SWAT+ rev.60.5.4\n" + body,
        encoding="utf-8",
    )
    return project


def test_check_rejects_rev60_project(rev60_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SWATPLUS_AI_NO_LOG", "1")
    result = CliRunner().invoke(root_app, ["check", str(rev60_project), "--skip-llm"])
    assert result.exit_code == 1
    assert "rev.60.5.4" in result.output
    assert "rev.61+" in result.output
