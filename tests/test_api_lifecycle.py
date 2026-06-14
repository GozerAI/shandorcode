"""Full analyze → query lifecycle on a fixture repo.

Pins the slim-payload contract that frontend code depends on. Multi-repo
refactor must preserve identical response shapes for /api/analyze (legacy shim).
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_analyze_returns_slim_payload(client: TestClient, tmp_repo: Path) -> None:
    resp = client.post("/api/analyze", json={"path": str(tmp_repo)})
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["status"] == "success"
    assert Path(body["path"]) == tmp_repo.resolve()
    assert isinstance(body["analysis_duration_ms"], int)
    assert body["analysis_duration_ms"] >= 0

    stats = body["stats"]
    assert stats["total_files"] >= 2
    assert stats["total_entities"] >= 4
    assert stats["total_dependencies"] >= 0
    assert stats["total_lines"] >= 0

    assert isinstance(body["entities"], list)
    assert len(body["entities"]) <= 100
    for entity in body["entities"]:
        assert {"id", "name", "type", "path", "start_line", "end_line"} <= entity.keys()

    assert isinstance(body["dependencies"], list)
    assert len(body["dependencies"]) <= 200
    assert isinstance(body["has_more"], bool)


def test_analyze_404_for_missing_path(client: TestClient, tmp_repo: Path) -> None:
    """Phase 1.3 fixed the broad `except Exception` swallowing HTTPException(404)."""
    resp = client.post("/api/analyze", json={"path": str(tmp_repo / "does-not-exist")})
    assert resp.status_code == 404


def test_analyze_then_current_returns_graph(analyzed_client: TestClient) -> None:
    resp = analyzed_client.get("/api/current")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    graph = body["graph"]
    assert "entities" in graph
    assert "dependencies" in graph
    assert graph["root_path"]


def test_analyze_then_history_includes_entry(analyzed_client: TestClient) -> None:
    resp = analyzed_client.get("/api/history")
    assert resp.status_code == 200
    history = resp.json()["history"]
    assert len(history) == 1
    entry = history[0]
    assert {"path", "timestamp", "files", "entities", "dependencies"} <= entry.keys()


def test_analyze_then_metrics_returns_summary(analyzed_client: TestClient) -> None:
    resp = analyzed_client.get("/api/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_files"] >= 2
    assert body["total_entities"] >= 4
    assert body["total_dependencies"] >= 0
    assert body["avg_complexity"] >= 0.0
    assert isinstance(body["language_breakdown"], dict)
    assert body["analyzed_at"]


def test_analyze_then_graph_returns_full_dict(analyzed_client: TestClient) -> None:
    resp = analyzed_client.get("/api/graph")
    assert resp.status_code == 200
    graph = resp.json()
    assert "entities" in graph
    assert "dependencies" in graph


def test_check_boundaries_returns_violation_list(analyzed_client: TestClient) -> None:
    """Phase 1.1 Analyzer ABC made check_boundaries available on every analyzer."""
    resp = analyzed_client.post(
        "/api/check-boundaries",
        json={"boundaries": [{"name": "core", "path": "src", "allowed_dependencies": []}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "violations" in body
    assert "count" in body
    assert isinstance(body["violations"], list)
    assert body["count"] == len(body["violations"])


def test_history_capped_at_ten(client: TestClient, tmp_repo: Path) -> None:
    for _ in range(12):
        resp = client.post("/api/analyze", json={"path": str(tmp_repo)})
        assert resp.status_code == 200
    history_resp = client.get("/api/history")
    assert history_resp.status_code == 200
    assert len(history_resp.json()["history"]) == 10
