# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""Thread-safe registry of RepoSessions backed by LRU eviction.

Replaces the module-level globals in ``src/api/server.py``. The API layer
asks the SessionManager for a session keyed by repo slug, runs operations
against it, and the manager handles housekeeping (registration, eviction,
access tracking).

Concurrency: a single ``RLock`` guards the slug→session map. Per-session
state has its own ``RLock`` inside ``RepoSession``, so two requests against
different slugs proceed in parallel.
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Iterable, List, Optional

from .base_analyzer import AnalyzerKind
from .repo_session import RepoSession, SessionStatus

logger = logging.getLogger(__name__)


_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class SessionManagerError(RuntimeError):
    """Raised for invalid slug or duplicate registration."""


class SessionManager:
    """Registry holding RepoSessions for the current process.

    LRU eviction policy: when the count of ``READY`` sessions exceeds
    ``max_hot``, the least-recently-accessed ready session has its heavy
    state dropped (graph/analyzer/ai_insights/watcher) via
    :py:meth:`RepoSession.evict`. Metadata stays; the next access lazily
    re-runs analysis.
    """

    def __init__(self, max_hot: int = 4) -> None:
        self.max_hot = max_hot
        self._sessions: dict[str, RepoSession] = {}
        self._lock = threading.RLock()

    def register(
        self,
        slug: str,
        path: str | Path,
        analyzer_kind: AnalyzerKind | str = AnalyzerKind.LIGHTNING,
        *,
        replace: bool = False,
    ) -> RepoSession:
        """Add a repo to the registry without analyzing it (lazy contract).

        Idempotent unless ``replace=True``: re-registering with the same
        slug returns the existing session (and updates path/analyzer_kind).
        """
        self._validate_slug(slug)
        resolved_kind = (
            analyzer_kind if isinstance(analyzer_kind, AnalyzerKind) else AnalyzerKind(analyzer_kind)
        )
        path_obj = Path(path).expanduser().resolve()
        if not path_obj.is_dir():
            raise SessionManagerError(f"path is not a directory: {path_obj}")

        with self._lock:
            existing = self._sessions.get(slug)
            if existing is not None and not replace:
                existing.path = path_obj
                existing.analyzer_kind = resolved_kind
                return existing
            if existing is not None and replace:
                existing.evict()
            session = RepoSession(slug=slug, path=path_obj, analyzer_kind=resolved_kind)
            self._sessions[slug] = session
            logger.info("registered repo session: slug=%s path=%s kind=%s",
                        slug, path_obj, resolved_kind.value)
            return session

    def unregister(self, slug: str) -> bool:
        """Drop a session entirely. Returns True if a session existed."""
        with self._lock:
            session = self._sessions.pop(slug, None)
            if session is None:
                return False
            session.evict()
            logger.info("unregistered repo session: slug=%s", slug)
            return True

    def get(self, slug: str) -> Optional[RepoSession]:
        """Return the session for slug if registered, else None.

        Does not touch the LRU clock. Use :py:meth:`get_for_use` when
        recording an access (e.g. inside a request handler).
        """
        with self._lock:
            return self._sessions.get(slug)

    def get_for_use(self, slug: str) -> Optional[RepoSession]:
        """Return the session and bump its access timestamp."""
        session = self.get(slug)
        if session is not None:
            session.touch()
        return session

    def list(self) -> List[RepoSession]:
        with self._lock:
            return list(self._sessions.values())

    def slugs(self) -> List[str]:
        with self._lock:
            return list(self._sessions.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    def __contains__(self, slug: object) -> bool:
        if not isinstance(slug, str):
            return False
        with self._lock:
            return slug in self._sessions

    def evict_lru(self) -> int:
        """Force LRU pass; returns count of sessions evicted.

        Normally called automatically after a session reaches READY, but
        also exposed so the API layer can trigger eviction (e.g. on
        memory pressure signals or shutdown).
        """
        evicted = 0
        with self._lock:
            ready = [s for s in self._sessions.values() if s.status is SessionStatus.READY]
            if len(ready) <= self.max_hot:
                return 0
            ready.sort(key=lambda s: s.last_accessed_at)
            for session in ready[: len(ready) - self.max_hot]:
                logger.info(
                    "evicting LRU session: slug=%s last_accessed=%s",
                    session.slug,
                    session.last_accessed_at.isoformat(),
                )
                session.evict()
                evicted += 1
        return evicted

    def refresh(self, slug: str) -> RepoSession:
        """Run analysis for slug (or raise if unknown). Triggers LRU pass."""
        session = self.get_for_use(slug)
        if session is None:
            raise SessionManagerError(f"unknown repo slug: {slug}")
        session.refresh()
        self.evict_lru()
        return session

    def reset(self) -> None:
        """Drop every session. Intended for tests + graceful shutdown."""
        with self._lock:
            for session in self._sessions.values():
                session.evict()
            self._sessions.clear()

    @staticmethod
    def _validate_slug(slug: str) -> None:
        if not isinstance(slug, str) or not _SLUG_RE.match(slug):
            raise SessionManagerError(
                f"invalid slug {slug!r}; must match {_SLUG_RE.pattern!r}"
            )

    def overview(self) -> dict:
        """Compact overview for /api/overview."""
        with self._lock:
            sessions = list(self._sessions.values())
        return {
            "total": len(sessions),
            "ready": sum(1 for s in sessions if s.status is SessionStatus.READY),
            "evicted": sum(1 for s in sessions if s.status is SessionStatus.EVICTED),
            "errored": sum(1 for s in sessions if s.status is SessionStatus.ERROR),
            "max_hot": self.max_hot,
            "repos": [s.to_summary() for s in sessions],
        }

    def register_many(
        self, entries: Iterable[tuple[str, str | Path, AnalyzerKind | str]]
    ) -> List[RepoSession]:
        """Convenience for workspace bootstrap (Phase 1.6)."""
        return [self.register(slug, path, kind) for slug, path, kind in entries]
