# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Christopher R. Arsenault / GozerAI

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

from ..core.analyzer import CodeAnalyzer
from ..core.optimized_analyzer import OptimizedAnalyzer
from ..core.lightning_analyzer import LightningAnalyzer
from ..core.models import ModuleBoundary, BoundaryViolation
from ..core.watcher import FileWatcher
from ..analyzers.ai_insights import AIInsights

logger = logging.getLogger(__name__)

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


# Initialize FastAPI app
app = FastAPI(
    title="ShandorCode",
    description="Real-time code visualization and analysis",
    version="0.1.0",
)

# Global state
analyzer: Optional[OptimizedAnalyzer] = None
ai_insights: Optional[AIInsights] = None
watcher: Optional[FileWatcher] = None
connected_clients: List[WebSocket] = []
current_graph = None
analysis_history = []


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
    """Serve the visualization interface"""
    return HTMLResponse(content=get_visualization_html())


@app.post("/api/analyze")
async def analyze_repository(request: AnalyzeRequest, tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """
    Analyze a code repository.
    
    Returns the complete code graph with entities and dependencies.
    """
    global analyzer, ai_insights, watcher, current_graph

    try:
        # Validate path
        repo_path = Path(request.path)
        if not repo_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {request.path}")

        # Use lightning analyzer for instant results
        logger.info(f"Analyzing repository: {request.path}")
        analyzer = LightningAnalyzer(str(repo_path.absolute()))

        # Lightning-fast analysis (<100ms)
        start_time = datetime.now()
        graph = analyzer.analyze_fast()
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Initialize AI insights
        ai_insights = AIInsights(graph)
        
        # Store in history
        analysis_history.insert(0, {
            "path": str(repo_path.absolute()),
            "timestamp": datetime.now().isoformat(),
            "files": graph.total_files,
            "entities": len(graph.entities),
            "dependencies": len(graph.dependencies),
        })
        if len(analysis_history) > 10:  # Keep last 10
            analysis_history.pop()
        
        # Store current graph
        current_graph = graph
        
        # Stop existing watcher
        if watcher:
            watcher.stop()
        
        # Start file watcher for real-time updates
        watcher = FileWatcher(
            str(repo_path.absolute()),
            callback=on_file_change,
            debounce_seconds=1.0,
        )
        
        # Start watcher in background
        asyncio.create_task(run_watcher())
        
        # Broadcast graph to all connected clients
        await broadcast_graph(graph)
        
        # Return SLIM analysis results (only essentials for instant load)
        # Send full details via separate endpoints as needed
        entities_slim = []
        for entity in list(graph.entities.values())[:100]:  # Limit initial load
            entities_slim.append({
                "id": entity.id,
                "name": entity.name,
                "type": entity.type.value,
                "path": entity.path,
                "start_line": entity.start_line,
                "end_line": entity.end_line,
            })

        deps_slim = []
        for dep in graph.dependencies[:200]:  # Limit initial dependencies
            deps_slim.append({
                "source": dep.source_id,
                "target": dep.target_id,
                "type": dep.type.value,
            })

        return {
            "status": "success",
            "path": str(repo_path.absolute()),
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
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/current")
async def get_current_analysis(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Get the current analysis data without re-analyzing"""
    global current_graph
    
    if current_graph is None:
        raise HTTPException(status_code=404, detail="No analysis available. Please analyze a repository first.")
    
    return {
        "status": "success",
        "graph": current_graph.to_dict(),
    }


@app.get("/api/history")
async def get_analysis_history(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """Get analysis history"""
    return {
        "status": "success",
        "history": analysis_history,
    }


@app.get("/api/metrics")
async def get_metrics(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """
    Get code metrics for the current repository.
    """
    global current_graph
    
    if current_graph is None:
        raise HTTPException(status_code=404, detail="No analysis available")
    
    graph = current_graph
    
    return MetricsResponse(
        total_files=graph.total_files,
        total_lines=sum(e.complexity.lines_of_code for e in graph.entities.values() if e.complexity),
        total_entities=len(graph.entities),
        total_dependencies=len(graph.dependencies),
        avg_complexity=graph.avg_complexity,
        language_breakdown={str(k): v for k, v in graph.language_breakdown.items()},
        analyzed_at=datetime.now().isoformat(),
        analysis_duration_ms=None,
    )


@app.get("/api/graph")
async def get_graph(tenant: dict = Depends(require_entitlement("shandorcode:basic"))):
    """
    Get the full dependency graph.
    """
    global current_graph
    
    if current_graph is None:
        raise HTTPException(status_code=404, detail="No analysis available")
    
    return current_graph.to_dict()


@app.post("/api/check-boundaries")
async def check_boundaries(request: BoundaryCheckRequest, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """
    Check module boundary violations.
    """
    global analyzer

    if analyzer is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    violations = analyzer.check_boundaries(request.boundaries)

    return {
        "violations": [v.dict() for v in violations],
        "count": len(violations),
    }


# ==================== AI Features Endpoints ====================

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


@app.post("/api/ai/search")
async def semantic_search(request: SearchRequest, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Semantic code search"""
    global ai_insights

    if ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    results = ai_insights.semantic_search(request.query, request.limit)

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
    global ai_insights

    if ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    smells = ai_insights.detect_code_smells()

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
    global ai_insights

    if ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    suggestions = ai_insights.suggest_refactoring(entity_id)

    return {"suggestions": suggestions}


@app.get("/api/ai/complexity-explained/{entity_id}")
async def explain_complexity(entity_id: str, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Explain complexity of an entity"""
    global ai_insights

    if ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    explanation = ai_insights.explain_complexity(entity_id)

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
    global ai_insights

    if ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    docs = ai_insights.generate_documentation(entity_id)

    if not docs:
        raise HTTPException(status_code=404, detail="Entity not found")

    return {"documentation": docs}


@app.get("/api/ai/similar-code/{entity_id}")
async def find_similar(entity_id: str, limit: int = 5, tenant: dict = Depends(require_entitlement("shandorcode:full"))):
    """Find code similar to an entity"""
    global ai_insights

    if ai_insights is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    similar = ai_insights.find_similar_code(entity_id, limit)

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
    """Get detailed code metrics"""
    global analyzer

    if analyzer is None:
        raise HTTPException(status_code=404, detail="No analysis available")

    return analyzer.get_metrics()



@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.
    """
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        # Send current graph if available
        if current_graph:
            await websocket.send_json({
                "type": "graph",
                "graph": current_graph.to_dict(),
            })
        
        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo ping messages
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})
                
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# Helper functions

async def broadcast_graph(graph):
    """Broadcast graph to all connected WebSocket clients"""
    message = {
        "type": "graph",
        "graph": graph.to_dict(),
    }
    
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except:
            disconnected.append(client)
    
    # Remove disconnected clients
    for client in disconnected:
        if client in connected_clients:
            connected_clients.remove(client)


def on_file_change(event):
    """Callback for file system changes"""
    logger.info(f"File change detected: {event}")
    
    # Re-analyze in background
    asyncio.create_task(reanalyze())


async def reanalyze():
    """Re-analyze the current repository"""
    global analyzer, current_graph
    
    if analyzer is None:
        return
    
    try:
        graph = analyzer.analyze()
        current_graph = graph
        await broadcast_graph(graph)
        logger.info("Re-analysis complete")
    except Exception as e:
        logger.error(f"Re-analysis failed: {e}")


async def run_watcher():
    """Run the file watcher"""
    global watcher
    
    if watcher:
        watcher.start()


def get_visualization_html() -> str:
    """Generate the visualization HTML page"""
    # Load fast UI from file (instant loading)
    ui_path = Path(__file__).parent.parent / "visualization" / "fast_ui.html"
    if ui_path.exists():
        return ui_path.read_text(encoding="utf-8")

    # Fallback to enhanced UI
    enhanced_ui_path = Path(__file__).parent.parent / "visualization" / "enhanced_ui.html"
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
    parser.add_argument("--path", help="Repository path to analyze on startup")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Auto-analyze if path provided
    if args.path:
        logger.info(f"Auto-analyzing repository: {args.path}")
        analyzer = CodeAnalyzer(args.path)
        graph = analyzer.analyze()
        current_graph = graph
        logger.info(f"Initial analysis complete: {graph.total_files} files")
    
    # Run server
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )
