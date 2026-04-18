"""Tests for ``swatplus_ai.diagnostics.rule.Rule``."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from swatplus_ai.diagnostics import Rule


def test_rule_load_minimal(rule_fixtures_dir: Path) -> None:
    rule = Rule.load(rule_fixtures_dir / "always_flag.yaml")
    assert rule.id == "test.always_flag"
    assert rule.severity == "warning"
    assert rule.stage == ("setup",)
    assert rule.requires == ()
    assert rule.check == "_test_always_flag"
    assert "{value}" in rule.message
    assert rule.references == ("synthetic_ref",)


def test_rule_load_wrong_stage(rule_fixtures_dir: Path) -> None:
    rule = Rule.load(rule_fixtures_dir / "wrong_stage.yaml")
    assert rule.stage == ("calibration",)
    assert rule.references == ()


def test_rule_load_with_requires(rule_fixtures_dir: Path) -> None:
    rule = Rule.load(rule_fixtures_dir / "requires_missing.yaml")
    assert rule.requires == ("no_such_project_attribute",)


def test_rule_is_frozen(rule_fixtures_dir: Path) -> None:
    rule = Rule.load(rule_fixtures_dir / "always_flag.yaml")
    with pytest.raises(ValidationError):
        rule.id = "other"  # type: ignore[misc]


def test_rule_rejects_missing_field(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text(
        "\n".join(
            [
                "id: test.bad",
                "severity: warning",
                "stage: [setup]",
                # check: deliberately missing
                "message: hello",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        Rule.load(p)


def test_rule_rejects_unknown_extra(tmp_path: Path) -> None:
    p = tmp_path / "extra.yaml"
    p.write_text(
        "\n".join(
            [
                "id: test.extra",
                "severity: warning",
                "stage: [setup]",
                "check: _test_always_flag",
                "message: hello",
                "not_a_field: 1",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        Rule.load(p)


def test_rule_rejects_bad_severity(tmp_path: Path) -> None:
    p = tmp_path / "sev.yaml"
    p.write_text(
        "\n".join(
            [
                "id: test.sev",
                "severity: fatal",
                "stage: [setup]",
                "check: _test_always_flag",
                "message: hi",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        Rule.load(p)


def test_rule_rejects_empty_stage(tmp_path: Path) -> None:
    p = tmp_path / "stage.yaml"
    p.write_text(
        "\n".join(
            [
                "id: test.stage",
                "severity: warning",
                "stage: []",
                "check: _test_always_flag",
                "message: hi",
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        Rule.load(p)


def test_rule_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    p = tmp_path / "scalar.yaml"
    p.write_text("just a string\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must contain a mapping"):
        Rule.load(p)
