"""Routes that return 404 when no analysis has been performed yet.

Pins the current single-repo "global state must be primed" coupling. Multi-repo
refactor (Phase 1.3) replaces these with per-repo 404s.
"""
from fastapi.testclient import TestClient


def test_current_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/current")
    assert resp.status_code == 404


def test_metrics_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/metrics")
    assert resp.status_code == 404


def test_graph_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/graph")
    assert resp.status_code == 404


def test_check_boundaries_404_when_no_analysis(client: TestClient) -> None:
    resp = client.post("/api/check-boundaries", json={"boundaries": []})
    assert resp.status_code == 404


def test_ai_search_404_when_no_analysis(client: TestClient) -> None:
    resp = client.post("/api/ai/search", json={"query": "anything"})
    assert resp.status_code == 404


def test_ai_code_smells_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/ai/code-smells")
    assert resp.status_code == 404


def test_ai_refactor_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/ai/refactor-suggestions/anything")
    assert resp.status_code == 404


def test_ai_complexity_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/ai/complexity-explained/anything")
    assert resp.status_code == 404


def test_ai_generate_docs_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/ai/generate-docs/anything")
    assert resp.status_code == 404


def test_ai_similar_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/ai/similar-code/anything")
    assert resp.status_code == 404


def test_metrics_detailed_404_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/metrics/detailed")
    assert resp.status_code == 404


def test_history_returns_empty_when_no_analysis(client: TestClient) -> None:
    resp = client.get("/api/history")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["history"] == []
