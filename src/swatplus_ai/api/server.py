"""FastAPI adapter for the swatplus-ai UI.

Surfaces parser + diagnostics output as ``/api/*`` JSON endpoints consumed
by ``ui/src/lib/api.ts``. Designed to run from ``swatplus-ai serve <path>``
on localhost only by default (``127.0.0.1:8765``).

Three endpoints are wired today — ``/api/project``, ``/api/findings``,
``/api/landuse`` — matching slice 3.3 of the UI refactor plan. Every
other endpoint the UI ``api.ts`` calls returns HTTP 501 with a stable
JSON body so the UI's ``EndpointNotImplementedError`` renders a clean
placeholder. The unimplemented list shrinks as later phases land
(hydrograph/iterations in Phase 3 calibration, chat in Phase 2 LLM).

Caching note: parsing a TxtInOut project touches ~60 input files, and
three endpoints each need the parsed tree. We attach a per-app
``lru_cache`` closure over the project path so a single session pays
the parse cost once. Tests that want a fresh cache just build a fresh
app — no global state to clear.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from swatplus_ai.api.adapters import (
    to_finding_vm,
    to_landuse_slices,
    to_project_meta,
)
from swatplus_ai.diagnostics import DiagnosticEngine, Finding
from swatplus_ai.parser.txtinout import TxtInOutProject

_UNIMPLEMENTED_PATHS: tuple[str, ...] = (
    "/api/hydrograph",
    "/api/iterations",
    "/api/cal-parameters",
    "/api/activity",
    "/api/chat-history",
)

_NOT_IMPLEMENTED_DETAIL = (
    "{path} is not implemented by the current swatplus-ai serve. "
    "Wait for a future migration slice — the UI renders a graceful placeholder."
)


def create_app(project_path: Path, *, static_dir: Path | None = None) -> FastAPI:
    """Build the FastAPI instance that backs ``swatplus-ai serve``.

    Parameters
    ----------
    project_path:
        TxtInOut folder to serve. Parsed once on first request via the
        per-app cache and reused across every endpoint.
    static_dir:
        Optional path to a built UI bundle (``ui/dist/``). When provided
        and the directory exists, it's mounted at ``/`` so the same
        process delivers both the UI assets and the API — the production
        single-binary shape. When absent, only ``/api/*`` is served, which
        is what ``pnpm -C ui dev`` expects (vite proxies ``/api``).
    """
    app = FastAPI(
        title="swatplus-ai",
        description="Local API for the SWAT+ai UI.",
        version="0.0.1",
    )

    @lru_cache(maxsize=1)
    def _load() -> TxtInOutProject:
        return TxtInOutProject.read(project_path)

    @lru_cache(maxsize=1)
    def _setup_findings() -> tuple[Finding, ...]:
        engine = DiagnosticEngine.from_builtin_rules()
        return tuple(engine.run(_load(), stage="setup"))

    @app.get("/api/project")
    def _project() -> JSONResponse:
        findings = _setup_findings()
        ready = not any(f.severity == "error" for f in findings)
        meta = to_project_meta(_load(), ready_to_run=ready)
        return JSONResponse(content=meta.model_dump(by_alias=True))

    @app.get("/api/findings")
    def _findings() -> JSONResponse:
        payload = [to_finding_vm(f).model_dump(by_alias=True) for f in _setup_findings()]
        return JSONResponse(content=payload)

    @app.get("/api/landuse")
    def _landuse() -> JSONResponse:
        slices = to_landuse_slices(_load())
        return JSONResponse(content=[s.model_dump(by_alias=True) for s in slices])

    for path in _UNIMPLEMENTED_PATHS:
        _register_not_implemented(app, path)

    if static_dir is not None and static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")

    return app


def _register_not_implemented(app: FastAPI, path: str) -> None:
    """Attach a 501 handler for ``path`` with a stable JSON error body.

    The UI client catches status 501 and throws ``EndpointNotImplementedError``;
    the detail body is what the component surfaces in the placeholder.
    """
    detail = _NOT_IMPLEMENTED_DETAIL.format(path=path)

    async def _handler() -> JSONResponse:
        return JSONResponse(status_code=501, content={"detail": detail})

    app.add_api_route(path, _handler, methods=["GET"], include_in_schema=False)


__all__ = ["create_app"]
