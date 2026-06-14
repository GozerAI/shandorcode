# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""
FastAPI server for ShandorCode visualization.

Provides REST API and WebSocket endpoints for real-time code analysis
and visualization.
"""

import logging
import asyncio
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import httpx
import json

from ..visualization.core.analyzer import CodeAnalyzer
from ..visualization.core.optimized_analyzer import OptimizedAnalyzer
from ..visualization.core.lightning_analyzer import LightningAnalyzer
from ..visualization.core.base_analyzer import AnalyzerKind
from ..visualization.core.models import ModuleBoundary, BoundaryViolation
from ..visualization.core.repo_session import RepoSession, SessionStatus
from ..visualization.core.session_manager import SessionManager, SessionManagerError
from ..visualization.core.watcher import FileWatcher
from ..visualization.core.watchtower_client import WatchtowerClient
from ..visualization.core.workspace_bootstrap import bootstrap as bootstrap_workspace, workspace_path
try:
    from ..visualization.analyzers.ai_insights import AIInsights
except ImportError:  # Pro feature — not in community edition
    AIInsights = None

logger = logging.getLogger(__name__)

# ── Path safety ───────────────────────────────────────────────────────────

ALLOWED_ROOTS = [
    os.path.expanduser("~"),
    "/tmp",
]


def _is_safe_path(path: str) -> bool:
    """Ensure path is under an allowed root and contains no traversal."""
    resolved = os.path.realpath(path)
    return any(resolved.startswith(os.path.realpath(root)) for root in ALLOWED_ROOTS)


ZUULTIMATE_BASE_URL = os.environ.get("ZUULTIMATE_BASE_URL", "http://localhost:8000")


# ── Zuultimate tenant auth ─────────────────────────────────────────────────

async def get_tenant(request: Request) -> dict:
    """Validate bearer token against Zuultimate and return tenant context."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth[7:]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{ZUULTIMATE_BASE_URL}/v1/identity/auth/validate",
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.RequestError as e:
        logger.error("Zuultimate unreachable: %s", e)
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired credentials")
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Auth service error")

    return resp.json()


def require_entitlement(entitlement: str):
    """Dependency factory: blocks if tenant lacks the required entitlement."""
    async def _check(tenant: dict = Depends(get_tenant)) -> dict:
        if entitlement not in tenant.get("entitlements", []):
            raise HTTPException(
                status_code=403,
                detail=f"Your plan does not include '{entitlement}'. Upgrade to access this feature.",
            )
        return tenant
    return _check


from contextlib import asynccontextmanager


@asynccontextmanager
async def _lifespan(app_: FastAPI):
    """Server lifespan: bootstrap workspace then yield."""
    try:
        bootstrap_workspace(session_manager)
    except Exception:
        logger.exception("workspace bootstrap raised; continuing with empty registry")
    yield


# Initialize FastAPI app
app = FastAPI(
    title="ShandorCode",
    description=(
        "ShandorCode platform — AI intelligence layer at /v1/intelligence/* "
        "plus the legacy code-visualization subsystem at /api/*."
    ),
    version="0.2.0",
    lifespan=_lifespan,
)

# Registered first so /v1/intelligence/* takes precedence in OpenAPI ordering.
# Visualization-side routes below stay backwards-compatible.

# SessionManager is the new source of truth for per-repo state. The remaining
# module-level names below are kept ONLY so the legacy single-repo /api/* shims
# (analyze/current/metrics/...) can continue to work; new code should reach for
# `session_manager` and `_legacy_current_slug` instead. They will be removed
# once the multi-repo dashboard UI ships (Phase 1.5).
session_manager: SessionManager = SessionManager(max_hot=4)
watchtower_client: WatchtowerClient = WatchtowerClient()
_legacy_current_slug: Optional[str] = None
analyzer: Optional[OptimizedAnalyzer] = None
ai_insights: Optional[AIInsights] = None
watcher: Optional[FileWatcher] = None
connected_clients: List[WebSocket] = []
current_graph = None
analysis_history: List[dict] = []


def get_session_manager() -> SessionManager:
    """FastAPI dependency that yields the process-wide SessionManager."""
    return session_manager


def _slug_from_path(path: Path) -> str:
    """Stable slug derived from the absolute path's basename.

    Lower-case, `[a-z0-9-]` only. Repos with the same basename collide; in
    that case workspace.json should pick explicit slugs instead. The legacy
    `/api/analyze` route, which only knows a path, accepts the collision.
    """
    name = path.name.lower() or "repo"
    safe = "".join(c if c.isalnum() or c == "-" else "-" for c in name).strip("-")
    return safe or "repo"


def _legacy_session() -> Optional[RepoSession]:
    """Resolve the session currently bound to the legacy single-repo routes."""
    if _legacy_current_slug is None:
        return None
    return session_manager.get(_legacy_current_slug)


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request to analyze a repository"""
    path: str


class BoundaryCheckRequest(BaseModel):
    """Request to check module boundaries"""
    boundaries: List[ModuleBoundary]


class MetricsResponse(BaseModel):
    """Response with code metrics"""
    total_files: int
    total_lines: int
    total_entities: int
    total_dependencies: int
    avg_complexity: float
    language_breakdown: dict
    analyzed_at: str
    analysis_duration_ms: Optional[int]


# API Endpoints

@app.get("/health")
async def health():
    """Health check endpoint (no auth required)."""
    return {"status": "ok", "service": "shandorcode"}


@app.get("/")
async def root():
    """Multi-repo workspace dashboard (Phase 1.5)."""
    dashboard_path = Path(__file__).parent.parent / "visualization" / "ui" / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"))
    return HTMLResponse(content=get_visualization_html())


@app.get("/legacy")
async def legacy_view():
    """Single-repo view kept for back-compat with the original /api/analyze flow."""
    return HTMLResponse(content=get_visualization_html())


def _slim_payload(graph, repo_path: Path, duration_ms: Optional[int]) -> dict:
    entities_slim = [
        {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type.value,
            "path": entity.path,
            "start_line": entity.start_line,
            "end_line": entity.end_line,
        }
        for entity in list(graph.entities.values())[:100]
    ]
    deps_slim = [
        {
            "source": dep.source_id,
            "target": dep.target_id,
            "type": dep.type.value,
        }
        for dep in graph.dependencies[:200]
    ]
    return {
        "status": "success",
        "path": str(repo_path),
        "analysis_duration_ms": duration_ms,
        "stats": {
            "total_files": graph.total_files,
            "total_entities": len(graph.entities),
            "total_dependencies": len(graph.dependencies),
            "total_lines": graph.total_lines,
        },
        "entities": entities_slim,
        "dependencies": deps_slim,
        "has_more": len(graph.entities) > 100,
    }


@app.post("/api/analyze")
async def analyze_repository(
    request: AnalyzeRequest,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Legacy single-repo entry point. Routes through SessionManager.

    Multi-repo callers should prefer ``POST /api/repos`` + ``POST
    /api/repos/{slug}/refresh`` (Phase 1.3 routes below). This endpoint
    stays for backward compatibility with the single-repo UI.
    """
    global _legacy_current_slug, analyzer, ai_insights, watcher, current_graph

    try:
        if ".." in str(request.path):
            raise HTTPException(status_code=400, detail="Path traversal not allowed")
        if not _is_safe_path(request.path):
            raise HTTPException(
                status_code=403,
                detail="Path not allowed. Analysis restricted to user workspace directories.",
            )

        repo_path = Path(request.path)
        if not repo_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")
        repo_path = repo_path.resolve()

        slug = _slug_from_path(repo_path)
        try:
            sm.register(slug, repo_path, AnalyzerKind.LIGHTNING, replace=True)
            session = sm.refresh(slug)
        except SessionManagerError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        _legacy_current_slug = slug
        analyzer = session.analyzer
        ai_insights = session.ai_insights
        current_graph = session.graph

        if watcher is not None:
            try:
                watcher.stop()
            except Exception:
                logger.warning("legacy watcher.stop() raised", exc_info=True)
        watcher = FileWatcher(
            str(repo_path),
            callback=on_file_change,
            debounce_seconds=1.0,
        )
        session.attach_watcher(watcher)
        asyncio.create_task(run_watcher())

        analysis_history.insert(
            0,
            {
                "path": str(repo_path),
                "timestamp": datetime.now().isoformat(),
                "files": session.graph.total_files,
                "entities": len(session.graph.entities),
                "dependencies": len(session.graph.dependencies),
            },
        )
        if len(analysis_history) > 10:
            analysis_history.pop()

        await broadcast_graph(session.graph)
        return _slim_payload(session.graph, repo_path, session.graph.analysis_duration_ms)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Analysis failed")
        raise HTTPException(status_code=500, detail="An internal error occurred")


@app.get("/api/current")
async def get_current_analysis(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Get the current legacy session's graph without re-analyzing."""
    session = _legacy_session()
    if session is None or session.graph is None:
        raise HTTPException(status_code=404, detail="No analysis available. Please analyze a repository first.")
    return {"status": "success", "graph": session.graph.to_dict()}


@app.get("/api/history")
async def get_analysis_history(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Get analysis history"""
    return {
        "status": "success",
        "history": analysis_history,
    }


def _require_legacy_graph():
    session = _legacy_session()
    if session is None or session.graph is None:
        raise HTTPException(status_code=404, detail="No analysis available")
    return session


@app.get("/api/metrics")
async def get_metrics(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Slim metrics for the legacy current session."""
    session = _require_legacy_graph()
    graph = session.graph
    return MetricsResponse(
        total_files=graph.total_files,
        total_lines=sum(
            e.complexity.lines_of_code for e in graph.entities.values() if e.complexity
        ),
        total_entities=len(graph.entities),
        total_dependencies=len(graph.dependencies),
        avg_complexity=graph.avg_complexity,
        language_breakdown={str(k): v for k, v in graph.language_breakdown.items()},
        analyzed_at=datetime.now().isoformat(),
        analysis_duration_ms=None,
    )


@app.get("/api/graph")
async def get_graph(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Full graph dump for the legacy current session."""
    session = _require_legacy_graph()
    return session.graph.to_dict()


@app.post("/api/check-boundaries")
async def check_boundaries(
    request: BoundaryCheckRequest,
    tenant: dict = Depends(require_entitlement("shandorcode:full")),
):
    """Check module boundary violations against the legacy current session."""
    session = _require_legacy_graph()
    violations = session.analyzer.check_boundaries(request.boundaries)
    return {
        "violations": [v.model_dump(mode="json") for v in violations],
        "count": len(violations),
    }


# ==================== AI Features Endpoints ====================

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


def _require_legacy_ai() -> AIInsights:
    session = _legacy_session()
    if session is None or session.ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")
    return session.ai_insights


@app.post("/api/ai/search")
async def semantic_search(request: SearchRequest, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Semantic code search"""
    insights = _require_legacy_ai()
    results = insights.semantic_search(request.query, request.limit)

    return {
        "query": request.query,
        "results": [
            {
                "id": r["entity"].id,
                "name": r["entity"].name,
                "type": r["entity"].type.value,
                "path": r["entity"].path,
                "score": r["score"],
                "relevance": r["relevance"]
            }
            for r in results
        ]
    }


@app.get("/api/ai/code-smells")
async def get_code_smells(tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Detect code smells"""
    insights = _require_legacy_ai()
    smells = insights.detect_code_smells()

    return {
        "smells": [
            {
                "type": s["type"],
                "severity": s["severity"],
                "message": s["message"],
                "suggestion": s["suggestion"],
                "entity": {
                    "id": s["entity"].id if "entity" in s else None,
                    "name": s["entity"].name if "entity" in s else None,
                    "path": s["entity"].path if "entity" in s else None,
                } if "entity" in s else None
            }
            for s in smells
        ],
        "count": len(smells)
    }


@app.get("/api/ai/refactor-suggestions/{entity_id}")
async def get_refactor_suggestions(entity_id: str, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Get refactoring suggestions for an entity"""
    insights = _require_legacy_ai()
    suggestions = insights.suggest_refactoring(entity_id)
    return {"suggestions": suggestions}


@app.get("/api/ai/complexity-explained/{entity_id}")
async def explain_complexity(entity_id: str, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Explain complexity of an entity"""
    insights = _require_legacy_ai()
    explanation = insights.explain_complexity(entity_id)

    if explanation is None:
        raise HTTPException(status_code=404, detail="Entity not found or has no complexity data")

    return {
        "entity": {
            "id": explanation["entity"].id,
            "name": explanation["entity"].name,
            "type": explanation["entity"].type.value,
        },
        "complexity": explanation["complexity"],
        "level": explanation["level"],
        "description": explanation["description"],
        "factors": explanation["factors"],
        "suggestions": explanation["suggestions"]
    }


@app.get("/api/ai/generate-docs/{entity_id}")
async def generate_docs(entity_id: str, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Generate documentation for an entity"""
    insights = _require_legacy_ai()
    docs = insights.generate_documentation(entity_id)
    if not docs:
        raise HTTPException(status_code=404, detail="Entity not found")
    return {"documentation": docs}


@app.get("/api/ai/similar-code/{entity_id}")
async def find_similar(entity_id: str, limit: int = 5, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Find code similar to an entity"""
    insights = _require_legacy_ai()
    similar = insights.find_similar_code(entity_id, limit)

    return {
        "similar": [
            {
                "id": s["entity"].id,
                "name": s["entity"].name,
                "type": s["entity"].type.value,
                "path": s["entity"].path,
                "similarity": s["similarity"]
            }
            for s in similar
        ]
    }


@app.get("/api/metrics/detailed")
async def get_detailed_metrics(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Get detailed code metrics for the legacy current session."""
    session = _require_legacy_graph()
    return session.analyzer.get_metrics()


# ==================== Multi-Repo (Phase 1.3) ====================

class RegisterRepoRequest(BaseModel):
    """Request body for ``POST /api/repos``."""

    slug: str
    path: str
    analyzer_kind: str = AnalyzerKind.LIGHTNING.value


def _require_session(sm: SessionManager, slug: str) -> RepoSession:
    session = sm.get_for_use(slug)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Unknown repo slug: {slug}")
    return session


def _require_ready(session: RepoSession) -> RepoSession:
    if session.graph is None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Repo '{session.slug}' has not been analyzed yet "
                "(POST /api/repos/{slug}/refresh first)"
            ),
        )
    return session


@app.get("/api/repos")
async def list_repos(
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """List every registered repo with current status (lazy: no probes fire)."""
    return {"repos": [s.to_summary() for s in sm.list()], "total": len(sm)}


@app.post("/api/repos", status_code=201)
async def register_repo(
    payload: RegisterRepoRequest,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Register a repo for analysis. Lazy: does NOT analyze."""
    try:
        kind = AnalyzerKind(payload.analyzer_kind)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Unsupported analyzer_kind: {payload.analyzer_kind!r}"
        )
    try:
        session = sm.register(payload.slug, payload.path, kind)
    except SessionManagerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return session.to_summary()


@app.delete("/api/repos/{slug}")
async def unregister_repo(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Drop a repo from the registry (also stops its watcher)."""
    global _legacy_current_slug
    if not sm.unregister(slug):
        raise HTTPException(status_code=404, detail=f"Unknown repo slug: {slug}")
    if _legacy_current_slug == slug:
        _legacy_current_slug = None
    return {"status": "deleted", "slug": slug}


@app.get("/api/repos/{slug}")
async def get_repo(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Return the summary card for a single repo."""
    return _require_session(sm, slug).to_summary()


@app.post("/api/repos/{slug}/refresh")
async def refresh_repo(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Run analysis for slug now. Returns the slim graph payload."""
    session = _require_session(sm, slug)
    try:
        sm.refresh(slug)
    except SessionManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await broadcast_repo(slug, "graph", session.graph.to_dict())
    return _slim_payload(session.graph, session.path, session.graph.analysis_duration_ms)


@app.get("/api/repos/{slug}/graph")
async def get_repo_graph(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    session = _require_ready(_require_session(sm, slug))
    return session.graph.to_dict()


@app.get("/api/repos/{slug}/health-badge")
async def repo_health_badge(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Backchannel to Watchtower for a per-repo health rollup.

    Phase 5 cross-tool integration. Returns ``{rollup_status, services}``
    so the multi-repo dashboard tile can render a status dot without
    forcing the browser to talk to Watchtower directly (avoids CORS).
    """
    if sm.get(slug) is None:
        raise HTTPException(status_code=404, detail=f"Unknown repo slug: {slug}")
    return await watchtower_client.health_for_repo(slug)


@app.get("/api/repos/{slug}/metrics")
async def get_repo_metrics(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    session = _require_ready(_require_session(sm, slug))
    graph = session.graph
    return MetricsResponse(
        total_files=graph.total_files,
        total_lines=sum(
            e.complexity.lines_of_code for e in graph.entities.values() if e.complexity
        ),
        total_entities=len(graph.entities),
        total_dependencies=len(graph.dependencies),
        avg_complexity=graph.avg_complexity,
        language_breakdown={str(k): v for k, v in graph.language_breakdown.items()},
        analyzed_at=datetime.now().isoformat(),
        analysis_duration_ms=graph.analysis_duration_ms,
    )


@app.get("/api/repos/{slug}/metrics/detailed")
async def get_repo_metrics_detailed(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    session = _require_ready(_require_session(sm, slug))
    return session.analyzer.get_metrics()


@app.post("/api/repos/{slug}/check-boundaries")
async def check_repo_boundaries(
    slug: str,
    request: BoundaryCheckRequest,
    tenant: dict = Depends(require_entitlement("shandorcode:full")),
    sm: SessionManager = Depends(get_session_manager),
):
    session = _require_ready(_require_session(sm, slug))
    violations = session.analyzer.check_boundaries(request.boundaries)
    return {
        "violations": [v.model_dump(mode="json") for v in violations],
        "count": len(violations),
    }


@app.post("/api/repos/{slug}/ai/search")
async def repo_semantic_search(
    slug: str,
    request: SearchRequest,
    tenant: dict = Depends(require_entitlement("shandorcode:full")),
    sm: SessionManager = Depends(get_session_manager),
):
    session = _require_ready(_require_session(sm, slug))
    results = session.ai_insights.semantic_search(request.query, request.limit)
    return {
        "query": request.query,
        "results": [
            {
                "id": r["entity"].id,
                "name": r["entity"].name,
                "type": r["entity"].type.value,
                "path": r["entity"].path,
                "score": r["score"],
                "relevance": r["relevance"],
            }
            for r in results
        ],
    }


@app.get("/api/repos/{slug}/ai/code-smells")
async def repo_code_smells(
    slug: str,
    tenant: dict = Depends(require_entitlement("shandorcode:full")),
    sm: SessionManager = Depends(get_session_manager),
):
    session = _require_ready(_require_session(sm, slug))
    smells = session.ai_insights.detect_code_smells()
    return {"smells": smells, "count": len(smells)}


@app.get("/api/overview")
async def overview(
    tenant: dict = Depends(require_entitlement("shandorcode:basic")),
    sm: SessionManager = Depends(get_session_manager),
):
    """Multi-repo summary: counts + per-repo cards. Drives Dashboard home."""
    return sm.overview()



# Phase 1.4 — per-WebSocket subscription registry.
# Maps each connected WebSocket to the set of repo_ids it wants events for.
# `"*"` is the wildcard that subscribes to every repo.
_ws_subscriptions: "dict[WebSocket, set[str]]" = {}


def _envelope(event_type: str, repo_id: Optional[str], payload: dict) -> dict:
    """Standard {type, repo_id, payload} envelope used by all WS broadcasts."""
    return {"type": event_type, "repo_id": repo_id, "payload": payload}


async def broadcast_repo(repo_id: Optional[str], event_type: str, payload: dict) -> None:
    """Send an event only to clients subscribed to repo_id (or wildcard)."""
    msg = _envelope(event_type, repo_id, payload)
    disconnected: list[WebSocket] = []
    for client in connected_clients:
        subs = _ws_subscriptions.get(client, {"*"})
        if "*" not in subs and (repo_id is None or repo_id not in subs):
            continue
        try:
            await client.send_json(msg)
        except Exception:
            disconnected.append(client)
    for c in disconnected:
        if c in connected_clients:
            connected_clients.remove(c)
        _ws_subscriptions.pop(c, None)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time updates with per-repo subscriptions.

    Protocol:
      * Server emits ``{type, repo_id, payload}`` envelopes.
      * Client may send ``ping`` (-> ``pong``) or a JSON message of the form
        ``{"action": "subscribe", "repo_ids": ["slug-a", "slug-b"]}`` /
        ``{"action": "subscribe", "repo_ids": ["*"]}`` /
        ``{"action": "unsubscribe", "repo_ids": [...]}``.
      * Default subscription is ``{"*"}`` so existing single-channel
        clients keep receiving every event.
      * On connect the server sends ``hello`` envelopes (one per registered
        repo) plus a legacy ``graph`` event if the legacy session is bound.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    _ws_subscriptions[websocket] = {"*"}

    try:
        for slug in session_manager.slugs():
            await websocket.send_json(
                _envelope("hello", slug, session_manager.get(slug).to_summary())
            )
        legacy = _legacy_session()
        if legacy is not None and legacy.graph is not None:
            await websocket.send_json(
                _envelope("graph", legacy.slug, legacy.graph.to_dict())
            )

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json(_envelope("keepalive", None, {}))
                continue

            if raw == "ping":
                await websocket.send_text("pong")
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(msg, dict):
                continue

            action = msg.get("action")
            repo_ids = msg.get("repo_ids") or []
            if not isinstance(repo_ids, list):
                continue

            current = _ws_subscriptions.setdefault(websocket, set())
            if action == "subscribe":
                for rid in repo_ids:
                    if isinstance(rid, str):
                        current.add(rid)
                await websocket.send_json(
                    _envelope("subscribed", None, {"repo_ids": sorted(current)})
                )
            elif action == "unsubscribe":
                for rid in repo_ids:
                    current.discard(rid)
                await websocket.send_json(
                    _envelope("subscribed", None, {"repo_ids": sorted(current)})
                )
            elif action == "list":
                await websocket.send_json(
                    _envelope("subscribed", None, {"repo_ids": sorted(current)})
                )

    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        _ws_subscriptions.pop(websocket, None)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        _ws_subscriptions.pop(websocket, None)


# Helper functions

async def broadcast_graph(graph) -> None:
    """Legacy single-channel broadcast for the legacy /api/analyze flow.

    Wraps the new envelope-based broadcaster so existing clients still
    receive a graph event when the legacy session updates.
    """
    legacy = _legacy_session()
    repo_id = legacy.slug if legacy is not None else None
    await broadcast_repo(repo_id, "graph", graph.to_dict())


def on_file_change(event):
    """Callback for file system changes"""
    logger.info(f"File change detected: {event}")
    
    # Re-analyze in background
    asyncio.create_task(reanalyze())


async def reanalyze():
    """Re-run analysis for the legacy current session and broadcast."""
    global current_graph, analyzer, ai_insights

    session = _legacy_session()
    if session is None:
        return

    try:
        session.refresh()
    except Exception as e:
        logger.error(f"Re-analysis failed: {e}")
        return

    current_graph = session.graph
    analyzer = session.analyzer
    ai_insights = session.ai_insights
    await broadcast_graph(session.graph)
    logger.info("Re-analysis complete for slug=%s", session.slug)


async def run_watcher():
    """Run the file watcher"""
    global watcher
    
    if watcher:
        watcher.start()


def get_visualization_html() -> str:
    """Generate the visualization HTML page"""
    # Load fast UI from file (instant loading)
    ui_path = Path(__file__).parent.parent / "visualization" / "ui" / "fast_ui.html"
    if ui_path.exists():
        return ui_path.read_text(encoding="utf-8")

    # Fallback to enhanced UI
    enhanced_ui_path = Path(__file__).parent.parent / "visualization" / "ui" / "enhanced_ui.html"
    if enhanced_ui_path.exists():
        return enhanced_ui_path.read_text(encoding="utf-8")

    # Fallback to basic embedded HTML
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShandorCode - Real-time Code Visualization</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
            color: #e0e0e0;
            overflow: hidden;
        }
        
        #app-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        
        /* Header */
        #header {
            background: rgba(10, 14, 26, 0.95);
            border-bottom: 2px solid #4fc3f7;
            padding: 15px 30px;
            backdrop-filter: blur(10px);
        }
        
        #header h1 {
            color: #4fc3f7;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        #header h1::before {
            content: "🏗️";
            font-size: 28px;
        }
        
        /* Path Input Section */
        .path-section {
            display: flex;
            gap: 10px;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .path-input {
            flex: 1;
            background: #1a1f2e;
            border: 2px solid #2d3748;
            color: #e0e0e0;
            padding: 12px 15px;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .path-input:focus {
            outline: none;
            border-color: #4fc3f7;
            box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.1);
        }
        
        .analyze-btn {
            background: linear-gradient(135deg, #4fc3f7 0%, #29b6f6 100%);
            color: #0a0e1a;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(79, 195, 247, 0.3);
        }
        
        .analyze-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(79, 195, 247, 0.4);
        }
        
        .analyze-btn:active {
            transform: translateY(0);
        }
        
        .analyze-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        /* Stats Bar */
        #stats {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .stat {
            background: rgba(79, 195, 247, 0.1);
            padding: 8px 16px;
            border-radius: 6px;
            border: 1px solid rgba(79, 195, 247, 0.3);
        }
        
        .stat-label {
            color: #888;
            font-size: 12px;
            display: block;
        }
        
        .stat-value {
            color: #4fc3f7;
            font-size: 18px;
            font-weight: 600;
            display: block;
        }
        
        /* Main Content */
        #main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        
        /* Sidebar */
        #sidebar {
            width: 320px;
            background: rgba(10, 14, 26, 0.95);
            border-right: 1px solid #2d3748;
            overflow-y: auto;
            padding: 20px;
        }
        
        .sidebar-section {
            margin-bottom: 25px;
        }
        
        .sidebar-title {
            color: #4fc3f7;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .btn {
            background: rgba(79, 195, 247, 0.1);
            color: #4fc3f7;
            border: 1px solid rgba(79, 195, 247, 0.3);
            padding: 10px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            width: 100%;
            margin-bottom: 8px;
            transition: all 0.2s;
        }
        
        .btn:hover {
            background: rgba(79, 195, 247, 0.2);
            border-color: #4fc3f7;
        }
        
        /* Search */
        .search-input {
            width: 100%;
            background: #1a1f2e;
            border: 1px solid #2d3748;
            color: #e0e0e0;
            padding: 10px 12px;
            border-radius: 6px;
            font-size: 13px;
            margin-bottom: 12px;
        }
        
        .search-input:focus {
            outline: none;
            border-color: #4fc3f7;
        }
        
        /* History */
        .history-item {
            background: rgba(79, 195, 247, 0.05);
            padding: 10px;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            border: 1px solid transparent;
            transition: all 0.2s;
        }
        
        .history-item:hover {
            border-color: rgba(79, 195, 247, 0.5);
            background: rgba(79, 195, 247, 0.1);
        }
        
        .history-path {
            color: #4fc3f7;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 4px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .history-stats {
            color: #888;
            font-size: 11px;
        }
        
        /* Entity Info Panel */
        #entity-info {
            background: rgba(79, 195, 247, 0.05);
            padding: 15px;
            border-radius: 8px;
            border: 1px solid rgba(79, 195, 247, 0.2);
        }
        
        .info-title {
            color: #4fc3f7;
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 12px;
        }
        
        .info-item {
            margin-bottom: 8px;
            font-size: 13px;
        }
        
        .info-label {
            color: #888;
            display: inline-block;
            width: 100px;
        }
        
        .info-value {
            color: #e0e0e0;
        }
        
        /* Visualization Area */
        #visualization {
            flex: 1;
            position: relative;
            overflow: hidden;
        }
        
        #graph {
            width: 100%;
            height: 100%;
        }
        
        /* Status Indicator */
        #status {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 10px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .status-connected {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
            color: #81c784;
        }
        
        .status-disconnected {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.5);
            color: #e57373;
        }
        
        .status-analyzing {
            background: rgba(255, 152, 0, 0.2);
            border: 1px solid rgba(255, 152, 0, 0.5);
            color: #ffb74d;
        }
        
        /* Graph Styles */
        .node {
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .node:hover {
            stroke: #4fc3f7;
            stroke-width: 3;
        }
        
        .node-file {
            fill: #4fc3f7;
        }
        
        .node-class {
            fill: #29b6f6;
        }
        
        .node-function {
            fill: #03a9f4;
        }
        
        .node-method {
            fill: #0288d1;
        }
        
        .link {
            stroke: rgba(79, 195, 247, 0.3);
            stroke-width: 1.5;
        }
        
        .node-label {
            fill: #e0e0e0;
            font-size: 11px;
            pointer-events: none;
            font-family: 'Segoe UI', sans-serif;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1f2e;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #4fc3f7;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #29b6f6;
        }
    </style>
</head>
<body>
    <div id="app-container">
        <div id="header">
            <h1>ShandorCode</h1>
            
            <div class="path-section">
                <input 
                    type="text" 
                    id="path-input" 
                    class="path-input" 
                    placeholder="Enter path to analyze (e.g., C:\\dev\\my-project)"
                />
                <button id="analyze-btn" class="analyze-btn" onclick="analyzeProject()">
                    Analyze
                </button>
            </div>
            
            <div id="stats">
                <div class="stat">
                    <span class="stat-label">Files</span>
                    <span class="stat-value" id="stat-files">-</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Entities</span>
                    <span class="stat-value" id="stat-entities">-</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Dependencies</span>
                    <span class="stat-value" id="stat-deps">-</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Avg Complexity</span>
                    <span class="stat-value" id="stat-complexity">-</span>
                </div>
            </div>
        </div>
        
        <div id="main-content">
            <div id="sidebar">
                <div class="sidebar-section">
                    <div class="sidebar-title">Controls</div>
                    <button class="btn" onclick="resetView()">🔄 Reset View</button>
                    <button class="btn" onclick="toggleDependencies()">🔗 Toggle Dependencies</button>
                    <button class="btn" onclick="exportSVG()">💾 Export SVG</button>
                </div>
                
                <div class="sidebar-section">
                    <div class="sidebar-title">Search</div>
                    <input 
                        type="text" 
                        id="search-input" 
                        class="search-input" 
                        placeholder="Search entities..."
                        oninput="searchEntities(this.value)"
                    />
                </div>
                
                <div class="sidebar-section">
                    <div class="sidebar-title">Recent Projects</div>
                    <div id="history-list"></div>
                </div>
                
                <div class="sidebar-section">
                    <div id="entity-info" style="display: none;">
                        <div class="info-title">Selected Entity</div>
                        <div id="info-content"></div>
                    </div>
                </div>
            </div>
            
            <div id="visualization">
                <svg id="graph"></svg>
                <div id="status">
                    <span id="status-text" class="status-disconnected">Disconnected</span>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // State
        let ws = null;
        let graphData = null;
        let showDependencies = true;
        let currentSimulation = null;
        let searchTerm = '';
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            connectWebSocket();
            loadHistory();
            
            // Allow Enter key to trigger analysis
            document.getElementById('path-input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') analyzeProject();
            });
        });
        
        // WebSocket Connection
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onopen = () => {
                updateStatus('connected', 'Connected');
                console.log('WebSocket connected');
            };
            
            ws.onclose = () => {
                updateStatus('disconnected', 'Disconnected');
                console.log('WebSocket disconnected, reconnecting...');
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'graph' && data.graph) {
                    graphData = data.graph;
                    updateStats(graphData);
                    renderGraph(graphData);
                }
            };
            
            // Keep connection alive
            setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000);
        }
        
        // Analyze Project
        async function analyzeProject() {
            const pathInput = document.getElementById('path-input');
            const analyzeBtn = document.getElementById('analyze-btn');
            const path = pathInput.value.trim();
            
            if (!path) {
                alert('Please enter a path');
                return;
            }
            
            try {
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = 'Analyzing...';
                updateStatus('analyzing', 'Analyzing...');
                
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path })
                });
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Analysis failed');
                }
                
                const result = await response.json();
                console.log(`Analysis complete in ${result.analysis_duration_ms}ms`);
                
                // Update UI
                graphData = result.graph;
                updateStats(graphData);
                renderGraph(graphData);
                loadHistory();
                
                updateStatus('connected', 'Connected');
                
            } catch (error) {
                console.error('Analysis error:', error);
                alert(`Analysis failed: ${error.message}`);
                updateStatus('disconnected', 'Error');
            } finally {
                analyzeBtn.disabled = false;
                analyzeBtn.textContent = 'Analyze';
            }
        }
        
        // Load History
        async function loadHistory() {
            try {
                const response = await fetch('/api/history');
                const data = await response.json();
                
                const historyList = document.getElementById('history-list');
                if (!data.history || data.history.length === 0) {
                    historyList.innerHTML = '<div style="color: #888; font-size: 12px;">No recent projects</div>';
                    return;
                }
                
                historyList.innerHTML = data.history.map(item => `
                    <div class="history-item" onclick="loadFromHistory('${item.path}')">
                        <div class="history-path" title="${item.path}">${item.path}</div>
                        <div class="history-stats">
                            ${item.files} files • ${item.entities} entities
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Failed to load history:', error);
            }
        }
        
        // Load from History
        function loadFromHistory(path) {
            document.getElementById('path-input').value = path;
            analyzeProject();
        }
        
        // Update Status
        function updateStatus(type, text) {
            const statusEl = document.getElementById('status-text');
            statusEl.textContent = text;
            statusEl.className = `status-${type}`;
        }
        
        // Update Stats
        function updateStats(graph) {
            document.getElementById('stat-files').textContent = graph.total_files || 0;
            document.getElementById('stat-entities').textContent = Object.keys(graph.entities || {}).length;
            document.getElementById('stat-deps').textContent = (graph.dependencies || []).length;
            document.getElementById('stat-complexity').textContent = (graph.avg_complexity || 0).toFixed(1);
        }
        
        // Render Graph
        function renderGraph(graph) {
            const svg = d3.select('#graph');
            svg.selectAll('*').remove();
            
            const container = document.getElementById('visualization');
            const width = container.clientWidth;
            const height = container.clientHeight;
            
            svg.attr('width', width).attr('height', height);
            
            // Prepare data
            const entities = graph.entities || {};
            const nodes = Object.values(entities)
                .filter(e => !searchTerm || e.name.toLowerCase().includes(searchTerm.toLowerCase()))
                .map(e => ({
                    id: e.id,
                    name: e.name,
                    type: e.type,
                    ...e
                }));
            
            const nodeIds = new Set(nodes.map(n => n.id));
            const links = (graph.dependencies || [])
                .filter(() => showDependencies)
                .filter(d => nodeIds.has(d.source_id) && nodeIds.has(d.target_id))
                .map(d => ({
                    source: d.source_id,
                    target: d.target_id,
                    type: d.type
                }));
            
            // Create force simulation
            const simulation = d3.forceSimulation(nodes)
                .force('link', d3.forceLink(links).id(d => d.id).distance(100))
                .force('charge', d3.forceManyBody().strength(-300))
                .force('center', d3.forceCenter(width / 2, height / 2))
                .force('collision', d3.forceCollide().radius(30));
            
            currentSimulation = simulation;
            
            // Draw links
            const link = svg.append('g')
                .selectAll('line')
                .data(links)
                .join('line')
                .attr('class', 'link');
            
            // Draw nodes
            const node = svg.append('g')
                .selectAll('circle')
                .data(nodes)
                .join('circle')
                .attr('class', d => `node node-${d.type}`)
                .attr('r', d => d.type === 'file' ? 8 : 5)
                .call(drag(simulation))
                .on('click', (event, d) => showEntityInfo(d));
            
            // Add labels
            const label = svg.append('g')
                .selectAll('text')
                .data(nodes)
                .join('text')
                .attr('class', 'node-label')
                .text(d => d.name)
                .attr('dx', 12)
                .attr('dy', 4);
            
            // Update positions
            simulation.on('tick', () => {
                link
                    .attr('x1', d => d.source.x)
                    .attr('y1', d => d.source.y)
                    .attr('x2', d => d.target.x)
                    .attr('y2', d => d.target.y);
                
                node
                    .attr('cx', d => d.x)
                    .attr('cy', d => d.y);
                
                label
                    .attr('x', d => d.x)
                    .attr('y', d => d.y);
            });
        }
        
        // Drag Behavior
        function drag(simulation) {
            function dragstarted(event) {
                if (!event.active) simulation.alphaTarget(0.3).restart();
                event.subject.fx = event.subject.x;
                event.subject.fy = event.subject.y;
            }
            
            function dragged(event) {
                event.subject.fx = event.x;
                event.subject.fy = event.y;
            }
            
            function dragended(event) {
                if (!event.active) simulation.alphaTarget(0);
                event.subject.fx = null;
                event.subject.fy = null;
            }
            
            return d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended);
        }
        
        // Show Entity Info
        function showEntityInfo(d) {
            const info = document.getElementById('entity-info');
            const content = document.getElementById('info-content');
            
            let html = `
                <div class="info-item">
                    <span class="info-label">Name:</span>
                    <span class="info-value">${d.name}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Type:</span>
                    <span class="info-value">${d.type}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Language:</span>
                    <span class="info-value">${d.language}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Path:</span>
                    <span class="info-value" style="word-break: break-all; font-size: 11px;">${d.path}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Lines:</span>
                    <span class="info-value">${d.start_line}-${d.end_line}</span>
                </div>
            `;
            
            if (d.complexity) {
                html += `
                    <div class="info-item">
                        <span class="info-label">Complexity:</span>
                        <span class="info-value">${d.complexity.cyclomatic_complexity}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">LOC:</span>
                        <span class="info-value">${d.complexity.lines_of_code}</span>
                    </div>
                `;
            }
            
            content.innerHTML = html;
            info.style.display = 'block';
        }
        
        // Control Functions
        function resetView() {
            searchTerm = '';
            document.getElementById('search-input').value = '';
            if (graphData) renderGraph(graphData);
        }
        
        function toggleDependencies() {
            showDependencies = !showDependencies;
            if (graphData) renderGraph(graphData);
        }
        
        function searchEntities(term) {
            searchTerm = term;
            if (graphData) renderGraph(graphData);
        }
        
        function exportSVG() {
            const svg = document.getElementById('graph');
            const serializer = new XMLSerializer();
            const svgString = serializer.serializeToString(svg);
            const blob = new Blob([svgString], { type: 'image/svg+xml' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'shandorcode-graph.svg';
            a.click();
            URL.revokeObjectURL(url);
        }
    </script>
</body>
</html>
"""


# Main entry point for running the server
if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="ShandorCode visualization server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument(
        "--workspace",
        help="Path to workspace.json (overrides $SHANDOR_WORKSPACE and ~/.shandor/workspace.json)",
    )
    parser.add_argument(
        "--path",
        help="(Legacy) repository path to analyze on startup; prefer --workspace",
    )

    args = parser.parse_args()

    if args.workspace:
        os.environ["SHANDOR_WORKSPACE"] = args.workspace

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logger.info("workspace will be loaded from %s", workspace_path())

    if args.path:
        logger.info(f"Auto-analyzing legacy repository: {args.path}")
        analyzer = CodeAnalyzer(args.path)
        graph = analyzer.analyze()
        current_graph = graph
        logger.info(f"Initial analysis complete: {graph.total_files} files")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )
