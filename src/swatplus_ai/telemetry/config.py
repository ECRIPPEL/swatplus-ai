"""Persistent on/off flag for SWAT+ai telemetry.

Telemetry is a **global** user preference, not per-project: a user who
disables it once shouldn't have to re-disable it in every TxtInOut they
touch. The flag lives in a tiny TOML file under the user's home dir (or
``$XDG_CONFIG_HOME`` when set, following the freedesktop convention).

Resolution order for :func:`is_enabled`:

1. The ``SWATPLUS_AI_NO_LOG`` env var wins — setting it to ``"1"``
   disables telemetry no matter what the config file says. This is the
   escape hatch for CI jobs and quick shell overrides.
2. Otherwise the TOML file is read; a missing file, missing section, or
   unparseable file all default to *enabled* (the roadmap's stance is
   "passive logging is on by default; disable is one CLI command away").

Writing is intentionally dumb: the schema is two lines, so we hand-write
the file instead of taking on ``tomli_w`` as a new runtime dep.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

ENV_DISABLE = "SWATPLUS_AI_NO_LOG"
_XDG_ENV = "XDG_CONFIG_HOME"
_PACKAGE_DIR = "swatplus-ai"
_CONFIG_FILENAME = "config.toml"


def config_path() -> Path:
    """Return the TOML path telemetry state reads from / writes to."""
    xdg = os.environ.get(_XDG_ENV)
    if xdg:
        return Path(xdg) / _PACKAGE_DIR / _CONFIG_FILENAME
    return Path.home() / f".{_PACKAGE_DIR}" / _CONFIG_FILENAME


def is_enabled() -> bool:
    """True unless the env var disables it or the config flag is False."""
    if os.environ.get(ENV_DISABLE) == "1":
        return False
    path = config_path()
    if not path.is_file():
        return True
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return True
    section = data.get("telemetry", {})
    if not isinstance(section, dict):
        return True
    flag = section.get("enabled", True)
    return bool(flag)


def set_enabled(flag: bool) -> None:
    """Persist the enable flag to :func:`config_path`."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "[telemetry]\nenabled = {}\n".format("true" if flag else "false")
    path.write_text(body, encoding="utf-8")


__all__ = ["ENV_DISABLE", "config_path", "is_enabled", "set_enabled"]
