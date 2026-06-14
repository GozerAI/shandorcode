"""Phase 1.6 tests: workspace.json → SessionManager bootstrap."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.api.server as server_mod
from src.visualization.core.base_analyzer import AnalyzerKind
from src.visualization.core.session_manager import SessionManager
from src.visualization.core.workspace_bootstrap import bootstrap


def _write_workspace(target: Path, repos: list[dict]) -> None:
    target.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "test workspace",
                "repos": repos,
                "services": [],
            }
        ),
        encoding="utf-8",
    )


def test_bootstrap_skips_when_file_missing(tmp_path: Path) -> None:
    sm = SessionManager()
    count = bootstrap(sm, workspace_file=tmp_path / "nope.json")
    assert count == 0
    assert len(sm) == 0


def test_bootstrap_registers_each_repo_lazily(tmp_path: Path) -> None:
    repo_a = tmp_path / "alpha"
    repo_b = tmp_path / "beta"
    for repo in (repo_a, repo_b):
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "x.py").write_text("def f(): pass\n", encoding="utf-8")

    workspace = tmp_path / "workspace.json"
    _write_workspace(
        workspace,
        repos=[
            {
                "slug": "alpha",
                "path": str(repo_a).replace("\\", "/"),
                "analyzer": "lightning",
            },
            {
                "slug": "beta",
                "path": str(repo_b).replace("\\", "/"),
                "analyzer": "full",
            },
        ],
    )

    sm = SessionManager()
    count = bootstrap(sm, workspace_file=workspace)
    assert count == 2
    assert {s.slug for s in sm.list()} == {"alpha", "beta"}
    # Lazy: no analysis fired during bootstrap.
    assert all(s.graph is None for s in sm.list())
    assert sm.get("beta").analyzer_kind is AnalyzerKind.FULL


def test_bootstrap_skips_missing_paths(tmp_path: Path, caplog) -> None:
    repo_real = tmp_path / "real"
    (repo_real / "src").mkdir(parents=True)
    (repo_real / "src" / "x.py").write_text("x=1\n", encoding="utf-8")

    workspace = tmp_path / "workspace.json"
    _write_workspace(
        workspace,
        repos=[
            {"slug": "real", "path": str(repo_real).replace("\\", "/")},
            {"slug": "ghost", "path": str(tmp_path / "ghost").replace("\\", "/")},
        ],
    )

    sm = SessionManager()
    with caplog.at_level("WARNING"):
        count = bootstrap(sm, workspace_file=workspace)
    assert count == 1
    assert "ghost" not in sm
    assert any("ghost" in rec.message for rec in caplog.records)


def test_bootstrap_runs_on_server_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "demo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "x.py").write_text("x=1\n", encoding="utf-8")
    workspace = tmp_path / "workspace.json"
    _write_workspace(
        workspace,
        repos=[{"slug": "demo", "path": str(repo).replace("\\", "/")}],
    )
    monkeypatch.setenv("SHANDOR_WORKSPACE", str(workspace))

    server_mod.session_manager.reset()
    server_mod.app.dependency_overrides[server_mod.get_tenant] = (
        lambda: {"tenant_id": "t", "entitlements": ["shandorcode:basic", "shandorcode:full"]}
    )
    try:
        with TestClient(server_mod.app, raise_server_exceptions=False) as client:
            resp = client.get("/api/repos")
            assert resp.status_code == 200
            slugs = {r["slug"] for r in resp.json()["repos"]}
            assert "demo" in slugs
    finally:
        server_mod.app.dependency_overrides.pop(server_mod.get_tenant, None)
