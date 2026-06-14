# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""Lazy registration of every workspace.json repo into the SessionManager.

Phase 1.6 of the multi-repo refactor. ShandorCode uses the shared loader at
``~/.shandor/lib/shandor_workspace.py`` so the same schema feeds the rest of
the Shandor suite (Watchtower, Dashboard) without duplication.

Lazy contract: registration only — no analyze, no watcher attachment. The
dashboard or a deliberate ``POST /api/repos/{slug}/refresh`` triggers work.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

from .base_analyzer import AnalyzerKind
from .session_manager import SessionManager, SessionManagerError

logger = logging.getLogger(__name__)


_DEFAULT_LIB = Path.home() / ".shandor" / "lib" / "shandor_workspace.py"
_DEFAULT_WORKSPACE = Path.home() / ".shandor" / "workspace.json"


def _load_shared_loader(path: Path = _DEFAULT_LIB) -> Optional[ModuleType]:
    """Import ``shandor_workspace`` from the shared ~/.shandor/lib directory."""
    if "shandor_workspace" in sys.modules:
        return sys.modules["shandor_workspace"]
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("shandor_workspace", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["shandor_workspace"] = module
    spec.loader.exec_module(module)
    return module


def workspace_path() -> Path:
    """Resolve the active workspace file (env override SHANDOR_WORKSPACE)."""
    override = os.environ.get("SHANDOR_WORKSPACE")
    return Path(override) if override else _DEFAULT_WORKSPACE


def bootstrap(
    sm: SessionManager,
    *,
    workspace_file: Optional[Path] = None,
    loader_lib: Path = _DEFAULT_LIB,
) -> int:
    """Register every workspace.json repo into ``sm``. Returns count registered.

    Idempotent: re-registering the same slug refreshes path/analyzer kind
    but never analyzes. Missing repo paths are skipped with a warning so a
    stale workspace doesn't block server startup.
    """
    target = Path(workspace_file) if workspace_file else workspace_path()
    if not target.is_file():
        logger.info("workspace bootstrap skipped: %s not found", target)
        return 0

    loader_module = _load_shared_loader(loader_lib)
    if loader_module is None:
        logger.warning(
            "workspace bootstrap skipped: shared loader missing at %s", loader_lib
        )
        return 0

    try:
        ws = loader_module.load_workspace(target)
    except loader_module.WorkspaceError as exc:
        logger.error("workspace bootstrap failed: %s", exc)
        return 0

    registered = 0
    for repo in ws.repos:
        if not repo.exists():
            logger.warning(
                "workspace repo %r path missing on disk: %s — skipping",
                repo.slug,
                repo.path,
            )
            continue
        try:
            sm.register(repo.slug, repo.path, AnalyzerKind(repo.analyzer))
            registered += 1
        except SessionManagerError as exc:
            logger.warning("could not register %r: %s", repo.slug, exc)
    logger.info(
        "workspace bootstrap registered %d/%d repos from %s",
        registered,
        len(ws.repos),
        target,
    )
    return registered
