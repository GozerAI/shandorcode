# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""Thin HTTP client for ShandorWatchtower.

Phase 5 cross-tool integration. ShandorCode's dashboard asks Watchtower for
a per-repo health rollup so each repo tile can render a small status dot
without the browser having to talk cross-origin. The client caches
responses briefly so a dashboard rendering 16 tiles doesn't issue 16
identical requests.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


_CACHE_TTL_SECONDS = 10.0


class WatchtowerClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout: float = 3.0,
    ) -> None:
        self.base_url = (
            base_url
            or os.environ.get("SHANDOR_WATCHTOWER_URL")
            or "http://127.0.0.1:8766"
        )
        self.timeout = timeout
        self._cache: dict[str, tuple[float, dict]] = {}
        self._lock = asyncio.Lock()

    async def health_for_repo(self, slug: str) -> dict:
        """Return ``{repo, services, rollup_status}`` from Watchtower.

        If Watchtower is unreachable, returns a soft fallback so the UI
        can still render — the status shows as ``unknown``.
        """
        now = time.monotonic()
        async with self._lock:
            cached = self._cache.get(slug)
            if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
                return cached[1]
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.base_url.rstrip('/')}/api/services/by-repo/{slug}"
                )
            if resp.status_code != 200:
                payload = {"repo": slug, "services": [], "rollup_status": "unknown"}
            else:
                payload = resp.json()
        except httpx.RequestError as exc:
            logger.debug("watchtower unreachable for %s: %s", slug, exc)
            payload = {"repo": slug, "services": [], "rollup_status": "unknown"}
        async with self._lock:
            self._cache[slug] = (now, payload)
        return payload

    def invalidate(self, slug: Optional[str] = None) -> None:
        if slug is None:
            self._cache.clear()
        else:
            self._cache.pop(slug, None)
