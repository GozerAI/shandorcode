# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""
Optimized code analyzer with parallel processing and caching.

Performance improvements:
- Parallel file parsing using multiprocessing
- File hash-based caching
- Incremental analysis
- Lazy loading of large graphs
"""

import logging
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
import time
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import lru_cache

from ..core.models import (
    ShandorCode,
    CodeEntity,
    Dependency,
    LanguageType,
)
from ..parsers.python_parser import PythonParser
from ..parsers.javascript_parser import JavaScriptParser, TypeScriptParser

logger = logging.getLogger(__name__)


class AnalysisCache:
    """Cache for parsed file results"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "index.json"
        self.index: Dict[str, str] = self._load_index()

    def _load_index(self) -> Dict[str, str]:
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text())
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}

    def _save_index(self):
        self.index_file.write_text(json.dumps(self.index, indent=2))

    def _get_file_hash(self, file_path: Path) -> str:
        """Get hash of file contents"""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    def get(self, file_path: Path) -> Optional[Tuple[List[CodeEntity], List[Dependency]]]:
        """Get cached parse results if file hasn't changed"""
        try:
            file_key = str(file_path)
            current_hash = self._get_file_hash(file_path)

            if file_key in self.index:
                cached_hash = self.index[file_key]
                if cached_hash == current_hash:
                    cache_file = self.cache_dir / f"{cached_hash}.json"
                    if cache_file.exists():
                        with open(cache_file, 'r') as f:
                            data = json.load(f)
                        entities = [CodeEntity(**e) for e in data["entities"]]
                        dependencies = [Dependency(**d) for d in data["dependencies"]]
                        return (entities, dependencies)
        except Exception as e:
            logger.debug(f"Cache miss for {file_path}: {e}")

        return None

    def set(self, file_path: Path, entities: List[CodeEntity], dependencies: List[Dependency]):
        """Cache parse results"""
        try:
            file_key = str(file_path)
            file_hash = self._get_file_hash(file_path)
            cache_file = self.cache_dir / f"{file_hash}.json"

            data = {
                "entities": [e.model_dump(mode="json") for e in entities],
                "dependencies": [d.model_dump(mode="json") for d in dependencies],
            }
            with open(cache_file, 'w') as f:
                json.dump(data, f)

            self.index[file_key] = file_hash
            self._save_index()
        except Exception as e:
            logger.warning(f"Failed to cache {file_path}: {e}")

    def clear_old_entries(self, keep_files: Set[str]):
        """Remove cache entries for deleted files"""
        to_remove = [k for k in self.index.keys() if k not in keep_files]
        for key in to_remove:
            del self.index[key]
        if to_remove:
            self._save_index()


def parse_file_worker(args: Tuple[str, str, str]) -> Optional[Tuple[str, List[CodeEntity], List[Dependency]]]:
    """Worker function for parallel parsing"""
    file_path, lang_str, root_path = args

    try:
        lang = LanguageType(lang_str)

        # Initialize parser (in worker process)
        if lang == LanguageType.PYTHON:
            parser = PythonParser()
        elif lang == LanguageType.JAVASCRIPT:
            parser = JavaScriptParser()
        elif lang == LanguageType.TYPESCRIPT:
            parser = TypeScriptParser()
        else:
            return None

        entities, dependencies = parser.parse_file(file_path)
        return (file_path, entities, dependencies)

    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")
        return None


class OptimizedAnalyzer:
    """
    High-performance code analyzer with caching and parallel processing.
    """

    LANGUAGE_MAP = {
        '.py': LanguageType.PYTHON,
        '.js': LanguageType.JAVASCRIPT,
        '.jsx': LanguageType.JAVASCRIPT,
        '.ts': LanguageType.TYPESCRIPT,
        '.tsx': LanguageType.TYPESCRIPT,
    }

    IGNORE_DIRS = {
        'node_modules', '__pycache__', '.git', '.venv', 'venv',
        'dist', 'build', '.pytest_cache', 'coverage', '.mypy_cache',
        '.next', '.nuxt', 'target', 'out'
    }

    def __init__(self, root_path: str, cache_enabled: bool = True, max_workers: int = 4):
        """
        Initialize optimized analyzer.

        Args:
            root_path: Root directory to analyze
            cache_enabled: Enable file-level caching
            max_workers: Number of parallel workers (default: 4)
        """
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {root_path}")

        self.cache_enabled = cache_enabled
        self.max_workers = max_workers

        # Initialize cache
        if cache_enabled:
            cache_dir = self.root_path / ".shandor_cache"
            self.cache = AnalysisCache(cache_dir)
        else:
            self.cache = None

        self.graph: Optional[ShandorCode] = None

        logger.info(f"Initialized optimized analyzer for {self.root_path} "
                   f"(cache={'enabled' if cache_enabled else 'disabled'}, "
                   f"workers={max_workers})")

    def analyze(self, incremental: bool = True) -> ShandorCode:
        """
        Analyze repository with optimizations.

        Args:
            incremental: Use cached results for unchanged files

        Returns:
            Complete code graph
        """
        start_time = time.time()
        logger.info("Starting optimized code analysis...")

        # Initialize graph
        graph = ShandorCode(root_path=str(self.root_path))

        # Discover files
        files = self._discover_files()
        logger.info(f"Found {len(files)} code files")

        if not files:
            graph.analysis_duration_ms = int((time.time() - start_time) * 1000)
            return graph

        # Prepare parsing tasks
        parse_tasks = []
        cached_results = []

        for file_path in files:
            lang = self._detect_language(file_path)
            if lang == LanguageType.UNKNOWN:
                continue

            # Try cache first
            if incremental and self.cache:
                cached = self.cache.get(file_path)
                if cached:
                    cached_results.append(cached)
                    continue

            # Queue for parsing
            parse_tasks.append((str(file_path), lang.value, str(self.root_path)))

        logger.info(f"Cache hits: {len(cached_results)}, Parse tasks: {len(parse_tasks)}")

        # Add cached results to graph
        for entities, dependencies in cached_results:
            for entity in entities:
                graph.add_entity(entity)
            for dep in dependencies:
                graph.add_dependency(dep)

        # Parse new/modified files in parallel
        if parse_tasks:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                futures = {executor.submit(parse_file_worker, task): task for task in parse_tasks}

                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        file_path_str, entities, dependencies = result

                        # Add to graph
                        for entity in entities:
                            graph.add_entity(entity)
                        for dep in dependencies:
                            graph.add_dependency(dep)

                        # Cache results
                        if self.cache:
                            self.cache.set(Path(file_path_str), entities, dependencies)

        # Clean cache
        if self.cache:
            self.cache.clear_old_entries({str(f) for f in files})

        # Calculate metrics
        self._calculate_metrics(graph)

        # Store duration
        duration_ms = int((time.time() - start_time) * 1000)
        graph.analysis_duration_ms = duration_ms

        self.graph = graph
        logger.info(
            f"Analysis complete: {graph.total_files} files, "
            f"{len(graph.entities)} entities, {len(graph.dependencies)} dependencies "
            f"in {duration_ms}ms"
        )

        return graph

    def analyze_file(self, file_path: Path) -> Tuple[List[CodeEntity], List[Dependency]]:
        """Analyze a single file (for incremental updates)"""
        lang = self._detect_language(file_path)
        if lang == LanguageType.UNKNOWN:
            return [], []

        # Check cache
        if self.cache:
            cached = self.cache.get(file_path)
            if cached:
                return cached

        # Parse
        if lang == LanguageType.PYTHON:
            parser = PythonParser()
        elif lang == LanguageType.JAVASCRIPT:
            parser = JavaScriptParser()
        elif lang == LanguageType.TYPESCRIPT:
            parser = TypeScriptParser()
        else:
            return [], []

        entities, dependencies = parser.parse_file(str(file_path))

        # Cache
        if self.cache:
            self.cache.set(file_path, entities, dependencies)

        return entities, dependencies

    def _discover_files(self) -> List[Path]:
        """Discover all code files in repository"""
        files = []
        for path in self.root_path.rglob('*'):
            # Skip ignored directories
            if any(ignored in path.parts for ignored in self.IGNORE_DIRS):
                continue

            # Check if it's a code file
            if path.is_file() and path.suffix in self.LANGUAGE_MAP:
                files.append(path)

        return files

    def _detect_language(self, file_path: Path) -> LanguageType:
        """Detect programming language from file extension"""
        return self.LANGUAGE_MAP.get(file_path.suffix, LanguageType.UNKNOWN)

    def _calculate_metrics(self, graph: ShandorCode):
        """Calculate aggregate metrics for the graph"""
        if not graph.entities:
            return

        entities = list(graph.entities.values())

        # Count files (unique paths)
        unique_paths = {e.path for e in entities}
        graph.total_files = len(unique_paths)

        # Total lines
        graph.total_lines = sum(e.end_line - e.start_line for e in entities)

        # Average complexity
        complexities = [
            e.complexity.cyclomatic_complexity
            for e in entities
            if e.complexity and e.complexity.cyclomatic_complexity
        ]
        graph.avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0

    def get_metrics(self) -> Dict:
        """Get detailed metrics about the codebase"""
        if not self.graph:
            return {}

        entities = list(self.graph.entities.values())

        # Complexity distribution
        complexity_dist = {'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
        for e in entities:
            if e.complexity and e.complexity.cyclomatic_complexity:
                cc = e.complexity.cyclomatic_complexity
                if cc <= 5:
                    complexity_dist['low'] += 1
                elif cc <= 10:
                    complexity_dist['medium'] += 1
                elif cc <= 20:
                    complexity_dist['high'] += 1
                else:
                    complexity_dist['very_high'] += 1

        # Dependency metrics
        dependencies = self.graph.dependencies
        avg_deps_per_entity = len(dependencies) / len(entities) if entities else 0

        # Find most connected entities
        dep_counts: Dict[str, int] = {}
        for dep in dependencies:
            dep_counts[dep.source_id] = dep_counts.get(dep.source_id, 0) + 1
            dep_counts[dep.target_id] = dep_counts.get(dep.target_id, 0) + 1

        most_connected = sorted(dep_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'total_files': self.graph.total_files,
            'total_entities': len(entities),
            'total_dependencies': len(dependencies),
            'total_lines': self.graph.total_lines,
            'avg_complexity': self.graph.avg_complexity,
            'complexity_distribution': complexity_dist,
            'avg_dependencies_per_entity': avg_deps_per_entity,
            'most_connected_entities': [
                {
                    'id': eid,
                    'name': self.graph.get_entity(eid).name if self.graph.get_entity(eid) else eid,
                    'connections': count
                }
                for eid, count in most_connected
            ],
            'language_breakdown': dict(self.graph.language_breakdown),
        }
