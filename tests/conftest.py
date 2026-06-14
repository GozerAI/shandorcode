"""Shared pytest fixtures for the ShandorCode safety net.

Pin existing single-repo behavior before the multi-repo refactor (Phase 1 of the
Shandor suite plan). Every test runs against `src.api.server.app` with auth
mocked via FastAPI dependency overrides.

The real FileWatcher.start() blocks in a `while self.running` loop, which would
hang the asyncio event loop when /api/analyze schedules `run_watcher()`. We
patch the FileWatcher symbol in src.api.server with a non-blocking stub so API
tests can complete; the real FileWatcher is exercised separately in
tests/test_watcher.py via background threads.
"""
from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

import src.api.server as server_mod
from src.api.server import app, get_tenant


class _StubWatcher:
    """Drop-in non-blocking replacement for FileWatcher used by API tests."""

    def __init__(self, path, callback, debounce_seconds=1.0):
        self.path = path
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True


@pytest.fixture(autouse=True)
def _stub_filewatcher(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace FileWatcher in the server namespace with the non-blocking stub."""
    monkeypatch.setattr(server_mod, "FileWatcher", _StubWatcher)


@pytest.fixture(autouse=True)
def _isolate_workspace_bootstrap(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Point SHANDOR_WORKSPACE at a non-existent path so lifespan bootstrap is a no-op.

    Individual tests that want to exercise the real bootstrap (e.g.
    test_workspace_bootstrap.py) override this via their own monkeypatch.
    """
    sentinel = tmp_path_factory.mktemp("ws") / "no-such-workspace.json"
    monkeypatch.setenv("SHANDOR_WORKSPACE", str(sentinel))


def _admin_tenant() -> dict:
    return {
        "tenant_id": "test-tenant",
        "entitlements": ["shandorcode:basic", "shandorcode:full"],
    }


def _basic_tenant() -> dict:
    return {
        "tenant_id": "test-tenant-basic",
        "entitlements": ["shandorcode:basic"],
    }


def _no_entitlement_tenant() -> dict:
    return {"tenant_id": "test-tenant-empty", "entitlements": []}


@pytest.fixture(autouse=True)
def reset_server_state() -> Iterator[None]:
    """Restore module-level globals + SessionManager between tests."""
    yield
    if server_mod.watcher is not None:
        try:
            server_mod.watcher.stop()
        except Exception:
            pass
    server_mod.analyzer = None
    server_mod.ai_insights = None
    server_mod.watcher = None
    server_mod.current_graph = None
    server_mod.analysis_history.clear()
    server_mod.connected_clients.clear()
    server_mod._legacy_current_slug = None
    server_mod.session_manager.reset()
    server_mod._ws_subscriptions.clear()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """TestClient with an admin tenant (both basic+full entitlements)."""
    app.dependency_overrides[get_tenant] = _admin_tenant
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_tenant, None)


@pytest.fixture
def client_basic_only() -> Iterator[TestClient]:
    """TestClient where the tenant has 'shandorcode:basic' but not 'shandorcode:full'."""
    app.dependency_overrides[get_tenant] = _basic_tenant
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_tenant, None)


@pytest.fixture
def client_no_entitlements() -> Iterator[TestClient]:
    """TestClient where the tenant exists but has no entitlements."""
    app.dependency_overrides[get_tenant] = _no_entitlement_tenant
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_tenant, None)


@pytest.fixture
def client_unauthenticated() -> Iterator[TestClient]:
    """TestClient with no auth override (calls real Zuultimate path → 401)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """A small Python+JS repo for analyzer fixtures."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "core.py").write_text(
        textwrap.dedent(
            """
            \"\"\"Core utilities for the demo project.\"\"\"

            import json


            class Greeter:
                \"\"\"Returns greetings.\"\"\"

                def __init__(self, name: str) -> None:
                    self.name = name

                def hello(self) -> str:
                    return f"hi {self.name}"


            def shout(message: str) -> str:
                if not message:
                    return ""
                if len(message) > 100:
                    raise ValueError("too long")
                return message.upper()
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "util.js").write_text(
        textwrap.dedent(
            """
            export function add(a, b) {
              return a + b;
            }

            export class Counter {
              constructor() {
                this.value = 0;
              }
              increment() {
                this.value += 1;
                return this.value;
              }
            }
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("demo repo", encoding="utf-8")
    return tmp_path


@pytest.fixture
def analyzed_client(client: TestClient, tmp_repo: Path) -> TestClient:
    """A client where /api/analyze has already been called against tmp_repo."""
    resp = client.post("/api/analyze", json={"path": str(tmp_repo)})
    assert resp.status_code == 200, resp.text
    return client


@pytest.fixture
def event_loop():
    """Provide a fresh event loop per test (avoids cross-test contamination)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
