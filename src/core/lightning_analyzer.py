# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Christopher R. Arsenault / GozerAI

"""
Lightning-fast analyzer for instant feedback.

Optimizations:
- Skip heavy parsing for small changes
- Return minimal data first, stream details
- Reuse parser instances
- Skip complexity calculation for preview
- Lazy entity loading
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
import time
import ast
import re

from ..core.models import (
    ShandorCode,
    CodeEntity,
    Dependency,
    LanguageType,
    EntityType,
    DependencyType,
    ComplexityMetrics,
)

logger = logging.getLogger(__name__)


class LightningAnalyzer:
    """Ultra-fast analyzer that returns results in <100ms"""

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
        '.next', '.nuxt', 'target', 'out', '.shandor_cache'
    }

    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {root_path}")

        self.graph: Optional[ShandorCode] = None
        logger.info(f"Initialized lightning analyzer for {self.root_path}")

    def analyze_fast(self) -> ShandorCode:
        """
        Lightning-fast analysis using AST instead of tree-sitter.
        Returns basic structure in <100ms.
        """
        start_time = time.time()
        logger.info("Starting lightning analysis...")

        graph = ShandorCode(root_path=str(self.root_path))

        # Discover files
        files = self._discover_files()
        logger.info(f"Found {len(files)} code files")

        # Fast parse each file
        for file_path in files:
            try:
                lang = self._detect_language(file_path)
                if lang == LanguageType.PYTHON:
                    self._fast_parse_python(file_path, graph)
                elif lang in [LanguageType.JAVASCRIPT, LanguageType.TYPESCRIPT]:
                    self._fast_parse_js(file_path, graph)
            except Exception as e:
                logger.debug(f"Error parsing {file_path}: {e}")

        # Quick metrics
        self._quick_metrics(graph)

        duration_ms = int((time.time() - start_time) * 1000)
        graph.analysis_duration_ms = duration_ms

        self.graph = graph
        logger.info(
            f"Lightning analysis complete: {graph.total_files} files, "
            f"{len(graph.entities)} entities in {duration_ms}ms"
        )

        return graph

    def _fast_parse_python(self, file_path: Path, graph: ShandorCode):
        """Fast Python parsing using built-in AST (no tree-sitter)"""
        try:
            code = file_path.read_text(encoding='utf-8')
            tree = ast.parse(code)

            # File entity
            file_id = f"file:{file_path}"
            file_entity = CodeEntity(
                id=file_id,
                name=file_path.name,
                type=EntityType.FILE,
                language=LanguageType.PYTHON,
                path=str(file_path.relative_to(self.root_path)),
                start_line=1,
                end_line=len(code.splitlines()),
            )
            graph.add_entity(file_entity)

            # Classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    entity_id = f"{file_id}:class:{node.name}"
                    entity = CodeEntity(
                        id=entity_id,
                        name=node.name,
                        type=EntityType.CLASS,
                        language=LanguageType.PYTHON,
                        path=str(file_path.relative_to(self.root_path)),
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        parent=file_id,
                        docstring=ast.get_docstring(node),
                    )
                    graph.add_entity(entity)
                    file_entity.children.append(entity_id)

                    # Methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_id = f"{entity_id}:method:{item.name}"
                            method = CodeEntity(
                                id=method_id,
                                name=item.name,
                                type=EntityType.METHOD,
                                language=LanguageType.PYTHON,
                                path=str(file_path.relative_to(self.root_path)),
                                start_line=item.lineno,
                                end_line=item.end_lineno or item.lineno,
                                parent=entity_id,
                                docstring=ast.get_docstring(item),
                            )
                            graph.add_entity(method)
                            entity.children.append(method_id)

                elif isinstance(node, ast.FunctionDef):
                    # Top-level function
                    if not isinstance(getattr(node, 'parent', None), ast.ClassDef):
                        entity_id = f"{file_id}:function:{node.name}"
                        entity = CodeEntity(
                            id=entity_id,
                            name=node.name,
                            type=EntityType.FUNCTION,
                            language=LanguageType.PYTHON,
                            path=str(file_path.relative_to(self.root_path)),
                            start_line=node.lineno,
                            end_line=node.end_lineno or node.lineno,
                            parent=file_id,
                            docstring=ast.get_docstring(node),
                        )
                        graph.add_entity(entity)
                        file_entity.children.append(entity_id)

            # Fast import detection
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Create simple dependency
                    module_name = None
                    if isinstance(node, ast.Import):
                        module_name = node.names[0].name if node.names else None
                    elif isinstance(node, ast.ImportFrom):
                        module_name = node.module

                    if module_name:
                        dep = Dependency(
                            source_id=file_id,
                            target_id=f"module:{module_name}",
                            type=DependencyType.IMPORT,
                            line_number=node.lineno,
                        )
                        graph.add_dependency(dep)

        except Exception as e:
            logger.debug(f"Fast parse failed for {file_path}: {e}")

    def _fast_parse_js(self, file_path: Path, graph: ShandorCode):
        """Fast JS/TS parsing using regex (no tree-sitter)"""
        try:
            code = file_path.read_text(encoding='utf-8')
            lines = code.splitlines()

            lang = self._detect_language(file_path)

            # File entity
            file_id = f"file:{file_path}"
            file_entity = CodeEntity(
                id=file_id,
                name=file_path.name,
                type=EntityType.FILE,
                language=lang,
                path=str(file_path.relative_to(self.root_path)),
                start_line=1,
                end_line=len(lines),
            )
            graph.add_entity(file_entity)

            # Quick regex patterns
            class_pattern = r'class\s+(\w+)'
            function_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)'
            import_pattern = r'import\s+.*from\s+[\'"]([^\'"]+)[\'"]'

            for i, line in enumerate(lines, 1):
                # Classes
                class_match = re.search(class_pattern, line)
                if class_match:
                    name = class_match.group(1)
                    entity_id = f"{file_id}:class:{name}"
                    entity = CodeEntity(
                        id=entity_id,
                        name=name,
                        type=EntityType.CLASS,
                        language=lang,
                        path=str(file_path.relative_to(self.root_path)),
                        start_line=i,
                        end_line=i + 10,  # Estimate
                        parent=file_id,
                    )
                    graph.add_entity(entity)
                    file_entity.children.append(entity_id)

                # Functions
                func_match = re.search(function_pattern, line)
                if func_match:
                    name = func_match.group(1) or func_match.group(2)
                    if name:
                        entity_id = f"{file_id}:function:{name}"
                        entity = CodeEntity(
                            id=entity_id,
                            name=name,
                            type=EntityType.FUNCTION,
                            language=lang,
                            path=str(file_path.relative_to(self.root_path)),
                            start_line=i,
                            end_line=i + 10,  # Estimate
                            parent=file_id,
                        )
                        graph.add_entity(entity)
                        file_entity.children.append(entity_id)

                # Imports
                import_match = re.search(import_pattern, line)
                if import_match:
                    module = import_match.group(1)
                    dep = Dependency(
                        source_id=file_id,
                        target_id=f"module:{module}",
                        type=DependencyType.IMPORT,
                        line_number=i,
                    )
                    graph.add_dependency(dep)

        except Exception as e:
            logger.debug(f"Fast parse failed for {file_path}: {e}")

    def _discover_files(self) -> List[Path]:
        """Fast file discovery with limits"""
        files = []
        max_files = 1000  # Safety limit

        for path in self.root_path.rglob('*'):
            if len(files) >= max_files:
                break

            # Quick ignore check
            if any(ignored in path.parts for ignored in self.IGNORE_DIRS):
                continue

            if path.is_file() and path.suffix in self.LANGUAGE_MAP:
                # Skip very large files
                if path.stat().st_size > 1_000_000:  # 1MB limit
                    continue
                files.append(path)

        return files

    def _detect_language(self, file_path: Path) -> LanguageType:
        return self.LANGUAGE_MAP.get(file_path.suffix, LanguageType.UNKNOWN)

    def _quick_metrics(self, graph: ShandorCode):
        """Calculate basic metrics without heavy computation"""
        if not graph.entities:
            return

        entities = list(graph.entities.values())

        # Count files
        unique_paths = {e.path for e in entities}
        graph.total_files = len(unique_paths)

        # Total lines (simple sum)
        graph.total_lines = sum(e.end_line - e.start_line for e in entities)

        # Skip complexity for speed
        graph.avg_complexity = 0.0

    def get_metrics(self) -> Dict:
        """Get basic metrics"""
        if not self.graph:
            return {}

        entities = list(self.graph.entities.values())

        return {
            'total_files': self.graph.total_files,
            'total_entities': len(entities),
            'total_dependencies': len(self.graph.dependencies),
            'total_lines': self.graph.total_lines,
            'language_breakdown': dict(self.graph.language_breakdown),
        }
