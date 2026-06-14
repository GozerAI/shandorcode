# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""Per-repository session container.

Phase 1.2 of the multi-repo refactor. Replaces the six module-level globals
(``analyzer``, ``ai_insights``, ``watcher``, ``current_graph`` etc.) with a
single per-repo bundle that the API layer can hand around explicitly.

Lifecycle:

* ``not_analyzed`` after :py:meth:`SessionManager.register` — metadata only,
  cheap (matches the lazy-load contract from the suite plan).
* ``analyzing`` while :py:meth:`refresh` is running.
* ``ready`` once a graph is in memory.
* ``evicted`` when SessionManager drops the heavy state to free RAM (see
  :py:meth:`evict`); the slug/path stay registered and the next access just
  triggers another refresh.
* ``error`` if analysis raised.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Optional

try:
    from ..analyzers.ai_insights import AIInsights
except ImportError:  # Pro feature — not in community edition
    AIInsights = None
from .base_analyzer import AbstractAnalyzer, AnalyzerKind, make_analyzer
from .models import ShandorCode

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    NOT_ANALYZED = "not_analyzed"
    ANALYZING = "analyzing"
    READY = "ready"
    EVICTED = "evicted"
    ERROR = "error"


@dataclass
class RepoSession:
    """All per-repo state that used to live in module-scope globals."""

    slug: str
    path: Path
    analyzer_kind: AnalyzerKind = AnalyzerKind.LIGHTNING
    status: SessionStatus = SessionStatus.NOT_ANALYZED
    last_analyzed_at: Optional[datetime] = None
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_error: Optional[str] = None
    analyzer: Optional[AbstractAnalyzer] = None
    graph: Optional[ShandorCode] = None
    ai_insights: Optional[AIInsights] = None
    watcher: Optional[object] = None  # FileWatcher; typed as object to avoid import cycle
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False, compare=False)

    @property
    def id(self) -> str:
        return self.slug

    @property
    def is_ready(self) -> bool:
        return self.status is SessionStatus.READY and self.graph is not None

    def touch(self) -> None:
        """Bump last_accessed_at; SessionManager uses this for LRU eviction."""
        self.last_accessed_at = datetime.now(UTC)

    def refresh(self) -> ShandorCode:
        """Run the configured analyzer and update graph + ai_insights.

        Lazy: callers (or SessionManager.get_for_use) decide when to invoke
        this. Synchronous; the API layer wraps it in run_in_threadpool when it
        wants to avoid blocking the event loop.
        """
        with self._lock:
            self.status = SessionStatus.ANALYZING
            try:
                analyzer = make_analyzer(self.analyzer_kind, str(self.path))
                graph = analyzer.analyze()
            except Exception as exc:
                self.status = SessionStatus.ERROR
                self.last_error = str(exc)
                logger.exception("analysis failed for repo %s", self.slug)
                raise
            self.analyzer = analyzer
            self.graph = graph
            self.ai_insights = AIInsights(graph) if AIInsights is not None else None
            self.status = SessionStatus.READY
            self.last_analyzed_at = datetime.now(UTC)
            self.last_error = None
            self.touch()
            return graph

    def attach_watcher(self, watcher) -> None:
        """Replace the active watcher (caller's responsibility to start it)."""
        with self._lock:
            self.detach_watcher()
            self.watcher = watcher

    def detach_watcher(self) -> None:
        with self._lock:
            if self.watcher is not None:
                try:
                    self.watcher.stop()
                except Exception:
                    logger.warning("watcher.stop() raised for repo %s", self.slug, exc_info=True)
            self.watcher = None

    def evict(self) -> None:
        """Drop heavy state (graph, analyzer, AI insights) but keep metadata.

        Used by SessionManager LRU. Watcher is also stopped — re-registering
        will reattach if requested.
        """
        with self._lock:
            self.detach_watcher()
            self.analyzer = None
            self.graph = None
            self.ai_insights = None
            self.status = SessionStatus.EVICTED
            self.last_error = None

    def to_summary(self) -> dict:
        """Lightweight dict for /api/repos and /api/overview."""
        return {
            "slug": self.slug,
            "path": str(self.path),
            "analyzer_kind": self.analyzer_kind.value,
            "status": self.status.value,
            "last_analyzed_at": (
                self.last_analyzed_at.isoformat() if self.last_analyzed_at else None
            ),
            "last_accessed_at": self.last_accessed_at.isoformat(),
            "last_error": self.last_error,
            "has_graph": self.graph is not None,
            "watch": self.watcher is not None,
            "stats": (
                {
                    "total_files": self.graph.total_files,
                    "total_entities": len(self.graph.entities),
                    "total_dependencies": len(self.graph.dependencies),
                    "total_lines": self.graph.total_lines,
                    "avg_complexity": self.graph.avg_complexity,
                }
                if self.graph is not None
                else None
            ),
        }
