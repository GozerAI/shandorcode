"""Phase 1.2 tests for RepoSession + SessionManager."""
from pathlib import Path

import pytest

from src.visualization.core.base_analyzer import AnalyzerKind
from src.visualization.core.repo_session import RepoSession, SessionStatus
from src.visualization.core.session_manager import SessionManager, SessionManagerError


def test_register_creates_pending_session(tmp_repo: Path) -> None:
    mgr = SessionManager()
    session = mgr.register("demo", tmp_repo)
    assert session.slug == "demo"
    assert session.status is SessionStatus.NOT_ANALYZED
    assert session.graph is None
    assert "demo" in mgr
    assert len(mgr) == 1


def test_register_idempotent(tmp_repo: Path) -> None:
    mgr = SessionManager()
    a = mgr.register("demo", tmp_repo)
    b = mgr.register("demo", tmp_repo)
    assert a is b


def test_register_replace_drops_state(tmp_repo: Path) -> None:
    mgr = SessionManager()
    first = mgr.register("demo", tmp_repo)
    mgr.refresh("demo")
    assert first.is_ready
    second = mgr.register("demo", tmp_repo, replace=True)
    assert second is not first
    assert second.status is SessionStatus.NOT_ANALYZED


def test_register_rejects_invalid_slug(tmp_repo: Path) -> None:
    mgr = SessionManager()
    with pytest.raises(SessionManagerError):
        mgr.register("Bad Slug!", tmp_repo)


def test_register_rejects_missing_path(tmp_path: Path) -> None:
    mgr = SessionManager()
    with pytest.raises(SessionManagerError):
        mgr.register("demo", tmp_path / "nope")


def test_unregister_removes_and_returns_true(tmp_repo: Path) -> None:
    mgr = SessionManager()
    mgr.register("demo", tmp_repo)
    assert mgr.unregister("demo") is True
    assert "demo" not in mgr
    assert mgr.unregister("demo") is False


def test_refresh_runs_analyzer_lazily(tmp_repo: Path) -> None:
    mgr = SessionManager()
    session = mgr.register("demo", tmp_repo, AnalyzerKind.LIGHTNING)
    assert session.graph is None
    mgr.refresh("demo")
    assert session.is_ready
    assert session.graph.total_files >= 2
    assert session.last_analyzed_at is not None


def test_lru_evicts_oldest_when_max_hot_exceeded(tmp_path: Path) -> None:
    mgr = SessionManager(max_hot=2)
    repos: list[Path] = []
    for slug in ("a", "b", "c"):
        repo = tmp_path / slug
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "x.py").write_text("def f(): pass\n", encoding="utf-8")
        repos.append(repo)
        mgr.register(slug, repo)
        mgr.refresh(slug)

    statuses = {s.slug: s.status for s in mgr.list()}
    assert statuses["a"] is SessionStatus.EVICTED  # oldest, dropped to free RAM
    assert statuses["b"] is SessionStatus.READY
    assert statuses["c"] is SessionStatus.READY


def test_evicted_session_recovers_on_refresh(tmp_path: Path) -> None:
    mgr = SessionManager(max_hot=1)
    for slug in ("a", "b"):
        repo = tmp_path / slug
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "x.py").write_text("def f(): pass\n", encoding="utf-8")
        mgr.register(slug, repo)
        mgr.refresh(slug)

    a = mgr.get("a")
    assert a is not None and a.status is SessionStatus.EVICTED
    mgr.refresh("a")
    assert a.is_ready


def test_get_for_use_bumps_access(tmp_repo: Path) -> None:
    mgr = SessionManager()
    mgr.register("demo", tmp_repo)
    before = mgr.get("demo").last_accessed_at
    after_session = mgr.get_for_use("demo")
    assert after_session.last_accessed_at >= before


def test_overview_summary_shape(tmp_repo: Path) -> None:
    mgr = SessionManager()
    mgr.register("demo", tmp_repo)
    overview = mgr.overview()
    assert overview["total"] == 1
    assert overview["ready"] == 0
    assert overview["max_hot"] == mgr.max_hot
    assert len(overview["repos"]) == 1
    summary = overview["repos"][0]
    assert summary["slug"] == "demo"
    assert summary["status"] == "not_analyzed"
    assert summary["has_graph"] is False
    assert summary["stats"] is None


def test_register_many(tmp_path: Path) -> None:
    repo_a = tmp_path / "a"
    repo_b = tmp_path / "b"
    for repo in (repo_a, repo_b):
        (repo / "src").mkdir(parents=True)
        (repo / "src" / "x.py").write_text("x=1\n", encoding="utf-8")

    mgr = SessionManager()
    sessions = mgr.register_many(
        [
            ("a", repo_a, AnalyzerKind.LIGHTNING),
            ("b", repo_b, "lightning"),
        ]
    )
    assert [s.slug for s in sessions] == ["a", "b"]
    assert {"a", "b"} == set(mgr.slugs())


def test_reset_drops_everything(tmp_repo: Path) -> None:
    mgr = SessionManager()
    mgr.register("demo", tmp_repo)
    mgr.refresh("demo")
    mgr.reset()
    assert len(mgr) == 0


def test_session_attach_and_detach_watcher(tmp_repo: Path) -> None:
    mgr = SessionManager()
    session = mgr.register("demo", tmp_repo)

    class _Stub:
        def __init__(self) -> None:
            self.stopped = False

        def stop(self) -> None:
            self.stopped = True

    first = _Stub()
    session.attach_watcher(first)
    assert session.watcher is first

    second = _Stub()
    session.attach_watcher(second)
    assert first.stopped is True
    assert session.watcher is second

    session.detach_watcher()
    assert second.stopped is True
    assert session.watcher is None


def test_refresh_on_unknown_slug_raises() -> None:
    mgr = SessionManager()
    with pytest.raises(SessionManagerError):
        mgr.refresh("ghost")
