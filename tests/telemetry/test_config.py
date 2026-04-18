"""Tests for the telemetry enable/disable config layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from swatplus_ai.telemetry import config


def test_is_enabled_defaults_true_when_config_absent(isolated_home: Path) -> None:
    assert not config.config_path().exists()
    assert config.is_enabled() is True


def test_set_and_read_roundtrip(isolated_home: Path) -> None:
    config.set_enabled(False)
    path = config.config_path()
    assert path.is_file()
    assert "enabled = false" in path.read_text(encoding="utf-8")
    assert config.is_enabled() is False

    config.set_enabled(True)
    assert "enabled = true" in path.read_text(encoding="utf-8")
    assert config.is_enabled() is True


def test_env_var_overrides_enabled_config(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config.set_enabled(True)
    monkeypatch.setenv(config.ENV_DISABLE, "1")
    assert config.is_enabled() is False


def test_env_var_only_overrides_on_exact_one(
    isolated_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arbitrary truthy values should not silently disable telemetry —
    # the env-var contract is "set to the literal string '1' to disable".
    config.set_enabled(True)
    monkeypatch.setenv(config.ENV_DISABLE, "true")
    assert config.is_enabled() is True


def test_xdg_path_used_when_env_var_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xdg = tmp_path / "xdg"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv(config.ENV_DISABLE, raising=False)
    expected = xdg / "swatplus-ai" / "config.toml"
    assert config.config_path() == expected
    config.set_enabled(False)
    assert expected.is_file()
    assert config.is_enabled() is False


def test_malformed_config_defaults_to_enabled(isolated_home: Path) -> None:
    path = config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("this is not valid toml [[[[", encoding="utf-8")
    assert config.is_enabled() is True


def test_missing_section_defaults_to_enabled(isolated_home: Path) -> None:
    path = config.config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[other]\nkey = 1\n", encoding="utf-8")
    assert config.is_enabled() is True
