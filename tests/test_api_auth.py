"""Auth gating behavior.

The current model checks bearer tokens against Zuultimate. We mock by overriding
get_tenant; this suite confirms entitlement gating still trips when the tenant
lacks the required scope.
"""
from pathlib import Path

from fastapi.testclient import TestClient


def test_basic_only_can_analyze(client_basic_only: TestClient, tmp_repo: Path) -> None:
    resp = client_basic_only.post("/api/analyze", json={"path": str(tmp_repo)})
    assert resp.status_code == 200


def test_basic_only_blocked_from_full_features(
    client_basic_only: TestClient, tmp_repo: Path
) -> None:
    client_basic_only.post("/api/analyze", json={"path": str(tmp_repo)})
    forbidden = client_basic_only.get("/api/ai/code-smells")
    assert forbidden.status_code == 403
    assert "shandorcode:full" in forbidden.json()["detail"]


def test_no_entitlements_blocked_everywhere(client_no_entitlements: TestClient) -> None:
    for path in [
        "/api/current",
        "/api/history",
        "/api/metrics",
        "/api/graph",
        "/api/metrics/detailed",
        "/api/ai/code-smells",
    ]:
        resp = client_no_entitlements.get(path)
        assert resp.status_code == 403, f"{path} expected 403, got {resp.status_code}"


def test_unauthenticated_health_still_works(client_unauthenticated: TestClient) -> None:
    resp = client_unauthenticated.get("/health")
    assert resp.status_code == 200
