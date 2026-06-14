# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""Common analyzer interface for ShandorCode.

Phase 1.1 of the multi-repo refactor. The three concrete analyzers
(CodeAnalyzer, LightningAnalyzer, OptimizedAnalyzer) historically had
incompatible signatures (``analyze()`` vs ``analyze_fast()`` vs
``analyze(incremental=True)``), and only ``CodeAnalyzer`` implemented
``check_boundaries``.

This module:

* declares ``AbstractAnalyzer`` so callers (the API layer, the upcoming
  ``RepoSession``) can treat any concrete analyzer the same way;
* provides shared ``check_boundaries`` and ``get_metrics`` implementations
  that operate on ``self.graph`` — eliminating the AttributeError that the
  ``/api/check-boundaries`` route hits today when paired with
  ``LightningAnalyzer``;
* exposes ``AnalyzerKind`` and ``make_analyzer`` so the workspace bootstrap
  (Phase 1.6) can pick an analyzer per repo from configuration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    BoundaryViolation,
    DependencyType,
    ModuleBoundary,
    ShandorCode,
)


class AnalyzerKind(str, Enum):
    """Selectable analyzer flavors."""

    LIGHTNING = "lightning"
    FULL = "full"
    OPTIMIZED = "optimized"


class AnalyzerError(RuntimeError):
    """Raised when an analyzer is asked for results before being run."""


class AbstractAnalyzer(ABC):
    """Base class every concrete analyzer must inherit from.

    Subclasses MUST set :pyattr:`kind` and implement :pymeth:`analyze`. They
    SHOULD store their last result on ``self.graph`` so the shared
    ``check_boundaries`` and ``get_metrics`` helpers can read it.
    """

    kind: AnalyzerKind  # set on each concrete subclass

    def __init__(self, root_path: str) -> None:
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {root_path}")
        self.graph: Optional[ShandorCode] = None

    @abstractmethod
    def analyze(self) -> ShandorCode:
        """Analyze the configured root and return the resulting graph.

        Implementations must populate ``self.graph`` and return it so callers
        can chain ``analyzer.analyze().to_dict()`` if convenient.
        """

    def check_boundaries(
        self, boundaries: List[ModuleBoundary]
    ) -> List[BoundaryViolation]:
        """Detect import-time violations of the supplied module boundaries.

        Shared implementation lifted from CodeAnalyzer so all three analyzer
        flavors honour ``/api/check-boundaries`` consistently.
        """
        if self.graph is None:
            raise AnalyzerError("must run analyze() before check_boundaries()")

        module_map: Dict[str, ModuleBoundary] = {b.path: b for b in boundaries}
        violations: List[BoundaryViolation] = []

        for dep in self.graph.dependencies:
            if dep.type != DependencyType.IMPORT:
                continue
            source_entity = self.graph.get_entity(dep.source_id)
            target_entity = self.graph.get_entity(dep.target_id)
            if not source_entity or not target_entity:
                continue
            source_module = self._find_module(source_entity.path, module_map)
            target_module = self._find_module(target_entity.path, module_map)
            if not source_module or not target_module:
                continue
            if source_module.name == target_module.name:
                continue
            if target_module.name not in source_module.allowed_dependencies:
                violations.append(
                    BoundaryViolation(
                        source_module=source_module.name,
                        target_module=target_module.name,
                        source_entity=source_entity.name,
                        target_entity=target_entity.name,
                        dependency_type=dep.type,
                        severity="error",
                        message=(
                            f"Module '{source_module.name}' cannot depend on "
                            f"'{target_module.name}' (violation at "
                            f"{source_entity.path}:{dep.line_number})"
                        ),
                    )
                )

        return violations

    def get_metrics(self) -> Dict[str, Any]:
        """Return a flat metrics dict for the most recent analysis."""
        if self.graph is None:
            raise AnalyzerError("must run analyze() before get_metrics()")
        graph = self.graph
        return {
            "total_files": graph.total_files,
            "total_lines": graph.total_lines,
            "total_entities": len(graph.entities),
            "total_dependencies": len(graph.dependencies),
            "avg_complexity": graph.avg_complexity,
            "language_breakdown": {str(k): v for k, v in graph.language_breakdown.items()},
            "analyzed_at": graph.analyzed_at.isoformat(),
            "analysis_duration_ms": graph.analysis_duration_ms,
        }

    @staticmethod
    def _find_module(
        entity_path: str, module_map: Dict[str, ModuleBoundary]
    ) -> Optional[ModuleBoundary]:
        normalized = entity_path.replace("\\", "/")
        best: Optional[ModuleBoundary] = None
        best_len = -1
        for prefix, boundary in module_map.items():
            normalized_prefix = prefix.replace("\\", "/")
            if normalized.startswith(normalized_prefix) and len(normalized_prefix) > best_len:
                best = boundary
                best_len = len(normalized_prefix)
        return best


def make_analyzer(kind: AnalyzerKind | str, root_path: str) -> AbstractAnalyzer:
    """Construct an analyzer of the requested flavor.

    Imports happen lazily so the base module stays free of cycle risk and
    callers can choose only the analyzer they actually need.
    """
    resolved = AnalyzerKind(kind) if not isinstance(kind, AnalyzerKind) else kind
    if resolved is AnalyzerKind.LIGHTNING:
        from .lightning_analyzer import LightningAnalyzer

        return LightningAnalyzer(root_path)
    if resolved is AnalyzerKind.FULL:
        from .analyzer import CodeAnalyzer

        return CodeAnalyzer(root_path)
    if resolved is AnalyzerKind.OPTIMIZED:
        from .optimized_analyzer import OptimizedAnalyzer

        return OptimizedAnalyzer(root_path)
    raise ValueError(f"Unsupported analyzer kind: {kind!r}")
