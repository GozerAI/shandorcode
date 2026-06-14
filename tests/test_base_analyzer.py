"""Phase 1.1 contract tests for AbstractAnalyzer."""
from pathlib import Path

import pytest

from src.visualization.core.analyzer import CodeAnalyzer
from src.visualization.core.base_analyzer import (
    AbstractAnalyzer,
    AnalyzerError,
    AnalyzerKind,
    make_analyzer,
)
from src.visualization.core.lightning_analyzer import LightningAnalyzer
from src.visualization.core.models import ModuleBoundary
from src.visualization.core.optimized_analyzer import OptimizedAnalyzer


def test_all_three_analyzers_inherit_abc() -> None:
    assert issubclass(CodeAnalyzer, AbstractAnalyzer)
    assert issubclass(LightningAnalyzer, AbstractAnalyzer)
    assert issubclass(OptimizedAnalyzer, AbstractAnalyzer)


def test_each_analyzer_declares_kind() -> None:
    assert CodeAnalyzer.kind is AnalyzerKind.FULL
    assert LightningAnalyzer.kind is AnalyzerKind.LIGHTNING
    assert OptimizedAnalyzer.kind is AnalyzerKind.OPTIMIZED


@pytest.mark.parametrize(
    "kind, expected_cls",
    [
        (AnalyzerKind.LIGHTNING, LightningAnalyzer),
        (AnalyzerKind.FULL, CodeAnalyzer),
        (AnalyzerKind.OPTIMIZED, OptimizedAnalyzer),
        ("lightning", LightningAnalyzer),
        ("full", CodeAnalyzer),
        ("optimized", OptimizedAnalyzer),
    ],
)
def test_make_analyzer_returns_correct_concrete(
    tmp_repo: Path, kind, expected_cls
) -> None:
    analyzer = make_analyzer(kind, str(tmp_repo))
    assert isinstance(analyzer, expected_cls)
    assert isinstance(analyzer, AbstractAnalyzer)
    assert analyzer.root_path == tmp_repo.resolve()


def test_make_analyzer_rejects_unknown_kind(tmp_repo: Path) -> None:
    with pytest.raises(ValueError):
        make_analyzer("turbo", str(tmp_repo))


def test_check_boundaries_before_analyze_raises(tmp_repo: Path) -> None:
    analyzer = LightningAnalyzer(str(tmp_repo))
    with pytest.raises(AnalyzerError):
        analyzer.check_boundaries([])


def test_get_metrics_before_analyze_raises(tmp_repo: Path) -> None:
    analyzer = CodeAnalyzer(str(tmp_repo))
    with pytest.raises(AnalyzerError):
        analyzer.get_metrics()


def test_lightning_analyze_alias_returns_same_as_fast(tmp_repo: Path) -> None:
    a = LightningAnalyzer(str(tmp_repo))
    g1 = a.analyze()
    b = LightningAnalyzer(str(tmp_repo))
    g2 = b.analyze_fast()
    assert g1.total_files == g2.total_files
    assert len(g1.entities) == len(g2.entities)


def test_check_boundaries_works_for_every_analyzer(tmp_repo: Path) -> None:
    boundaries = [
        ModuleBoundary(name="src", path="", allowed_dependencies=[]),
    ]
    for kind in AnalyzerKind:
        analyzer = make_analyzer(kind, str(tmp_repo))
        analyzer.analyze()
        violations = analyzer.check_boundaries(boundaries)
        assert isinstance(violations, list)


def test_get_metrics_works_for_every_analyzer(tmp_repo: Path) -> None:
    for kind in AnalyzerKind:
        analyzer = make_analyzer(kind, str(tmp_repo))
        analyzer.analyze()
        metrics = analyzer.get_metrics()
        assert isinstance(metrics, dict)
        assert metrics["total_files"] >= 2
