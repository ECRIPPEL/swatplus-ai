"""Built-in check functions for the diagnostic rule engine.

Importing this package triggers registration of every bundled check
function (one ``@register_check(name)`` per function) into the module-level
registry read by :class:`~swatplus_ai.diagnostics.engine.DiagnosticEngine`.

The ``diagnostics`` top-level package imports this subpackage for its
side effect — callers constructing an engine via
``DiagnosticEngine.from_builtin_rules()`` therefore never have to import
the check modules themselves. Submodules are split by rule namespace
(``setup``, ``hru``, ``chan``, ``wx``, ...), mirroring the rule-id
convention documented in ``swatplus-ai_architecture.md``.
"""

from __future__ import annotations

from swatplus_ai.diagnostics.checks import chan as _chan  # noqa: F401 — side-effect import
from swatplus_ai.diagnostics.checks import hru as _hru  # noqa: F401 — side-effect import
from swatplus_ai.diagnostics.checks import setup as _setup  # noqa: F401 — side-effect import
from swatplus_ai.diagnostics.checks import wb as _wb  # noqa: F401 — side-effect import
from swatplus_ai.diagnostics.checks import wx as _wx  # noqa: F401 — side-effect import
