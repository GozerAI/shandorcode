"""Document the single-repo global-state coupling we are about to refactor.

Each of these assertions encodes a known limitation of the current design.
After Phase 1.3 (API refactor), these tests should be UPDATED — not deleted —
to assert the per-repo isolation that replaces them.
"""
from pathlib import Path

import pytest

import src.api.server as server_mod
from fastapi.testclient import TestClient


def test_module_holds_six_globals_today() -> None:
    expected_globals = {
        "analyzer",
        "ai_insights",
        "watcher",
        "current_graph",
        "analysis_history",
        "connected_clients",
    }
    actual = {name for name in expected_globals if hasattr(server_mod, name)}
    assert actual == expected_globals


def test_second_analyze_overwrites_first(client: TestClient, tmp_path: Path) -> None:
    """Today: analyzing repo B replaces repo A's graph entirely.

    Multi-repo refactor must keep both available concurrently.
    """
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    (repo_a / "src").mkdir(parents=True)
    (repo_b / "src").mkdir(parents=True)
    (repo_a / "src" / "alpha.py").write_text("def alpha(): pass\n", encoding="utf-8")
    (repo_b / "src" / "beta.py").write_text("def beta(): pass\n", encoding="utf-8")

    resp_a = client.post("/api/analyze", json={"path": str(repo_a)})
    assert resp_a.status_code == 200
    current_after_a = client.get("/api/current").json()["graph"]
    assert current_after_a["root_path"].endswith("a")

    resp_b = client.post("/api/analyze", json={"path": str(repo_b)})
    assert resp_b.status_code == 200
    current_after_b = client.get("/api/current").json()["graph"]
    assert current_after_b["root_path"].endswith("b")
    assert not current_after_b["root_path"].endswith("a")


def test_analysis_history_is_shared_across_calls(
    client: TestClient, tmp_path: Path
) -> None:
    """history endpoint reflects every analyze call regardless of which repo."""
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    (repo_a / "src").mkdir(parents=True)
    (repo_b / "src").mkdir(parents=True)
    (repo_a / "src" / "alpha.py").write_text("x=1\n", encoding="utf-8")
    (repo_b / "src" / "beta.py").write_text("y=2\n", encoding="utf-8")

    client.post("/api/analyze", json={"path": str(repo_a)})
    client.post("/api/analyze", json={"path": str(repo_b)})

    history = client.get("/api/history").json()["history"]
    assert len(history) == 2
    paths = [Path(h["path"]).name for h in history]
    assert "b" in paths and "a" in paths
