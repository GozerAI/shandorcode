"""Phase 5 cross-tool integration tests."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.api.server as server_mod


class _StubWatchtower:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[str] = []

    async def health_for_repo(self, slug: str) -> dict:
        self.calls.append(slug)
        return {**self.payload, "repo": slug}

    def invalidate(self, slug=None) -> None:
        pass


def test_health_badge_404_for_unknown(client: TestClient) -> None:
    resp = client.get("/api/repos/ghost/health-badge")
    assert resp.status_code == 404


def test_health_badge_hits_watchtower(
    client: TestClient, tmp_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = _StubWatchtower(
        {"services": [{"name": "example-api", "status": "healthy"}], "rollup_status": "healthy"}
    )
    monkeypatch.setattr(server_mod, "watchtower_client", stub)
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    resp = client.get("/api/repos/demo/health-badge")
    assert resp.status_code == 200
    body = resp.json()
    assert body["repo"] == "demo"
    assert body["rollup_status"] == "healthy"
    assert stub.calls == ["demo"]


def test_health_badge_graceful_when_watchtower_down(
    client: TestClient, tmp_repo: Path
) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    # No stub: real WatchtowerClient will fail to connect and fall back.
    resp = client.get("/api/repos/demo/health-badge")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rollup_status"] == "unknown"
