"""Phase 1.3 tests for the new /api/repos/* routes."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_list_repos_empty(client: TestClient) -> None:
    resp = client.get("/api/repos")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"repos": [], "total": 0}


def test_register_repo_lazy(client: TestClient, tmp_repo: Path) -> None:
    resp = client.post(
        "/api/repos",
        json={"slug": "demo", "path": str(tmp_repo)},
    )
    assert resp.status_code == 201
    summary = resp.json()
    assert summary["slug"] == "demo"
    assert summary["status"] == "not_analyzed"
    assert summary["has_graph"] is False
    assert summary["stats"] is None


def test_register_repo_rejects_invalid_slug(client: TestClient, tmp_repo: Path) -> None:
    resp = client.post("/api/repos", json={"slug": "Bad Slug", "path": str(tmp_repo)})
    assert resp.status_code == 400


def test_register_repo_rejects_unknown_analyzer(client: TestClient, tmp_repo: Path) -> None:
    resp = client.post(
        "/api/repos",
        json={"slug": "demo", "path": str(tmp_repo), "analyzer_kind": "turbo"},
    )
    assert resp.status_code == 400


def test_get_repo_404_when_unknown(client: TestClient) -> None:
    resp = client.get("/api/repos/ghost")
    assert resp.status_code == 404


def test_get_repo_returns_summary(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    resp = client.get("/api/repos/demo")
    assert resp.status_code == 200
    assert resp.json()["slug"] == "demo"


def test_refresh_runs_analysis(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    resp = client.post("/api/repos/demo/refresh")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["stats"]["total_files"] >= 2

    summary = client.get("/api/repos/demo").json()
    assert summary["status"] == "ready"
    assert summary["has_graph"] is True
    assert summary["stats"]["total_entities"] >= 4


def test_graph_409_when_not_analyzed(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    resp = client.get("/api/repos/demo/graph")
    assert resp.status_code == 409


def test_graph_returns_after_refresh(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    client.post("/api/repos/demo/refresh")
    resp = client.get("/api/repos/demo/graph")
    assert resp.status_code == 200
    graph = resp.json()
    assert "entities" in graph
    assert "dependencies" in graph


def test_metrics_endpoints_work(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    client.post("/api/repos/demo/refresh")
    slim = client.get("/api/repos/demo/metrics").json()
    assert slim["total_files"] >= 2
    detailed = client.get("/api/repos/demo/metrics/detailed").json()
    assert isinstance(detailed, dict)


def test_check_boundaries_per_repo(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    client.post("/api/repos/demo/refresh")
    resp = client.post(
        "/api/repos/demo/check-boundaries",
        json={"boundaries": [{"name": "core", "path": "src", "allowed_dependencies": []}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "violations" in body and "count" in body


def test_ai_search_per_repo(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    client.post("/api/repos/demo/refresh")
    resp = client.post(
        "/api/repos/demo/ai/search", json={"query": "greet", "limit": 3}
    )
    assert resp.status_code == 200
    assert resp.json()["query"] == "greet"


def test_unregister_drops_repo(client: TestClient, tmp_repo: Path) -> None:
    client.post("/api/repos", json={"slug": "demo", "path": str(tmp_repo)})
    resp = client.delete("/api/repos/demo")
    assert resp.status_code == 200
    assert client.get("/api/repos/demo").status_code == 404


def test_unregister_404_for_unknown(client: TestClient) -> None:
    resp = client.delete("/api/repos/ghost")
    assert resp.status_code == 404


def test_overview_summarizes_workspace(client: TestClient, tmp_path: Path) -> None:
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    for repo in (repo_a, repo_b):
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "x.py").write_text("def f(): pass\n", encoding="utf-8")
    client.post("/api/repos", json={"slug": "a", "path": str(repo_a)})
    client.post("/api/repos", json={"slug": "b", "path": str(repo_b)})
    client.post("/api/repos/b/refresh")

    overview = client.get("/api/overview").json()
    assert overview["total"] == 2
    assert overview["ready"] == 1
    assert {r["slug"] for r in overview["repos"]} == {"a", "b"}


def test_two_repos_are_isolated(client: TestClient, tmp_path: Path) -> None:
    """Multi-repo isolation: analyzing repo B does NOT affect repo A's graph."""
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    (repo_a / "src").mkdir(parents=True)
    (repo_b / "src").mkdir(parents=True)
    (repo_a / "src" / "alpha.py").write_text("def alpha(): pass\n", encoding="utf-8")
    (repo_b / "src" / "beta.py").write_text("def beta(): pass\n", encoding="utf-8")

    for slug, path in (("a", repo_a), ("b", repo_b)):
        client.post("/api/repos", json={"slug": slug, "path": str(path)})
        client.post(f"/api/repos/{slug}/refresh")

    graph_a = client.get("/api/repos/a/graph").json()
    graph_b = client.get("/api/repos/b/graph").json()
    assert graph_a["root_path"].endswith("a")
    assert graph_b["root_path"].endswith("b")
    assert any("alpha" in eid for eid in graph_a["entities"])
    assert any("beta" in eid for eid in graph_b["entities"])
