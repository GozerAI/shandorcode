"""Direct exercise of the three analyzers.

Phase 1.1 introduces an AbstractAnalyzer; this suite locks the entry-point
contracts (analyze() / analyze_fast() / analyze(incremental=...)) before they
are rationalized.
"""
from pathlib import Path

import pytest

from src.visualization.core.analyzer import CodeAnalyzer
from src.visualization.core.lightning_analyzer import LightningAnalyzer
from src.visualization.core.optimized_analyzer import OptimizedAnalyzer


def test_lightning_analyze_fast_returns_graph(tmp_repo: Path) -> None:
    analyzer = LightningAnalyzer(str(tmp_repo))
    graph = analyzer.analyze_fast()
    assert graph.total_files >= 2
    assert len(graph.entities) >= 4
    assert graph.analysis_duration_ms is not None
    assert graph.analysis_duration_ms >= 0


def test_lightning_get_metrics(tmp_repo: Path) -> None:
    analyzer = LightningAnalyzer(str(tmp_repo))
    analyzer.analyze_fast()
    metrics = analyzer.get_metrics()
    assert isinstance(metrics, dict)


def test_code_analyzer_full_analyze(tmp_repo: Path) -> None:
    analyzer = CodeAnalyzer(str(tmp_repo))
    graph = analyzer.analyze()
    assert graph.total_files >= 2
    assert len(graph.entities) >= 1


def test_code_analyzer_get_metrics(tmp_repo: Path) -> None:
    analyzer = CodeAnalyzer(str(tmp_repo))
    analyzer.analyze()
    metrics = analyzer.get_metrics()
    assert isinstance(metrics, dict)


def test_optimized_analyzer_analyze(tmp_repo: Path) -> None:
    analyzer = OptimizedAnalyzer(str(tmp_repo), cache_enabled=False, max_workers=2)
    graph = analyzer.analyze(incremental=False)
    assert graph.total_files >= 2


def test_optimized_analyzer_with_cache(tmp_repo: Path) -> None:
    cache_a = OptimizedAnalyzer(str(tmp_repo), cache_enabled=True, max_workers=2)
    graph_a = cache_a.analyze(incremental=False)
    cache_b = OptimizedAnalyzer(str(tmp_repo), cache_enabled=True, max_workers=2)
    graph_b = cache_b.analyze(incremental=True)
    assert graph_a.total_files == graph_b.total_files


def test_lightning_rejects_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        LightningAnalyzer(str(tmp_path / "nope"))
