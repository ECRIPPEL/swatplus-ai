"""Tests for :mod:`swatplus_ai.api.server`.

The server is a thin translator: parse the project once, run the setup
rules once, expose adapters via three endpoints, and return 501 for
everything the UI calls but the backend can't answer yet. These tests
pin all three shapes.

Fixture note: :class:`TestClient` uses httpx under the hood and is
synchronous, so the ``async`` 501 handlers are exercised via the same
path the real uvicorn loop would use — no ``pytest.mark.asyncio``
needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from swatplus_ai.api.server import create_app

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
MINIMAL = FIXTURES_DIR / "txtinout_minimal"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(MINIMAL))


def test_project_endpoint_returns_camel_case_meta(client: TestClient) -> None:
    res = client.get("/api/project")
    assert res.status_code == 200
    data = res.json()
    # Every camelCase key declared in schemas.ts's ProjectMeta must be
    # present — a snake_case leak would silently break the UI.
    for key in (
        "name",
        "path",
        "simulationStart",
        "simulationEnd",
        "warmupYears",
        "hrus",
        "channels",
        "weatherStations",
        "modelVersion",
        "outfallChannel",
        "climate",
        "areaKm2",
        "readyToRun",
        "outletLat",
        "outletLon",
        "biome",
    ):
        assert key in data, f"missing {key} in /api/project response"
    # No snake_case on the wire.
    assert "warmup_years" not in data
    assert "ready_to_run" not in data
    assert data["name"] == MINIMAL.name


def test_findings_endpoint_returns_list_of_camel_case_findings(client: TestClient) -> None:
    res = client.get("/api/findings")
    assert res.status_code == 200
    payload = res.json()
    assert isinstance(payload, list)
    if payload:
        finding = payload[0]
        assert "ruleId" in finding
        assert "rule_ref" not in finding
        assert finding["severity"] in {"info", "warning", "error"}


def test_landuse_endpoint_returns_list_of_slices(client: TestClient) -> None:
    res = client.get("/api/landuse")
    assert res.status_code == 200
    payload = res.json()
    assert isinstance(payload, list)
    for slice_ in payload:
        assert "className" in slice_
        assert "areaKm2" in slice_
        # Minimal fixture may round to zero, but the key shape must hold.
        assert isinstance(slice_["pct"], (int, float))


@pytest.mark.parametrize(
    "path",
    [
        "/api/hydrograph",
        "/api/iterations",
        "/api/cal-parameters",
        "/api/activity",
        "/api/chat-history",
    ],
)
def test_unimplemented_endpoints_return_501_with_detail(client: TestClient, path: str) -> None:
    res = client.get(path)
    assert res.status_code == 501
    body = res.json()
    assert "detail" in body
    assert path in body["detail"]
    assert "not implemented" in body["detail"]


def test_ready_to_run_is_false_when_setup_has_errors() -> None:
    """Smoke: if a setup rule raises an error-severity finding on the
    minimal fixture, the ``readyToRun`` flag must reflect that.

    The minimal fixture might produce zero errors (that's fine — the rule
    set evolves). The contract we pin here is the formula: ``readyToRun``
    is ``True`` iff no error-severity findings came out of the setup stage.
    """
    with TestClient(create_app(MINIMAL)) as client:
        project = client.get("/api/project").json()
        findings = client.get("/api/findings").json()
    has_error = any(f["severity"] == "error" for f in findings)
    assert project["readyToRun"] is (not has_error)


def test_static_dir_mount_is_skipped_when_absent(tmp_path: Path) -> None:
    missing = tmp_path / "dist-does-not-exist"
    with TestClient(create_app(MINIMAL, static_dir=missing)) as client:
        # API still works …
        assert client.get("/api/project").status_code == 200
        # … and no index.html materialises at /.
        assert client.get("/").status_code == 404


def test_static_dir_mount_serves_index_when_present(tmp_path: Path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("<html><body>UI</body></html>", encoding="utf-8")
    with TestClient(create_app(MINIMAL, static_dir=static)) as client:
        res = client.get("/")
        assert res.status_code == 200
        assert "<body>UI</body>" in res.text


def test_per_app_cache_parses_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hitting /api/project, /api/findings, /api/landuse on the same app
    should trigger exactly one :meth:`TxtInOutProject.read` call — the
    point of the lru_cache closure. A regression here would mean every
    UI navigation re-parses ~60 input files.
    """
    import swatplus_ai.api.server as server_module
    from swatplus_ai.parser.txtinout import TxtInOutProject

    call_count = {"n": 0}
    original = TxtInOutProject.read

    def _counting_read(path: Path) -> TxtInOutProject:
        call_count["n"] += 1
        return original(path)

    monkeypatch.setattr(server_module.TxtInOutProject, "read", staticmethod(_counting_read))

    with TestClient(create_app(MINIMAL)) as client:
        client.get("/api/project")
        client.get("/api/findings")
        client.get("/api/landuse")

    assert call_count["n"] == 1
