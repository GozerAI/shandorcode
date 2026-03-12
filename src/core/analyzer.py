# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / 1450 Enterprises LLC

"""
Main code analyzer that coordinates parsing and graph building.

This is the core orchestrator that:
1. Discovers files in a repository
2. Routes to appropriate parsers
3. Builds the code graph
4. Calculates metrics
5. Detects architecture violations
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
import time
from datetime import datetime

from ..core.models import (
    ShandorCode,
    CodeEntity,
    Dependency,
    ModuleBoundary,
    BoundaryViolation,
    LanguageType,
    DependencyType,
)
from ..parsers.python_parser import PythonParser
from ..parsers.javascript_parser import JavaScriptParser, TypeScriptParser

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """
    Main analyzer for code repositories.
    
    Analyzes code structure, dependencies, and complexity across
    multiple programming languages.
    """
    
    # File extension to language mapping
    LANGUAGE_MAP = {
        '.py': LanguageType.PYTHON,
        '.js': LanguageType.JAVASCRIPT,
        '.jsx': LanguageType.JAVASCRIPT,
        '.ts': LanguageType.TYPESCRIPT,
        '.tsx': LanguageType.TYPESCRIPT,
    }
    
    # Directories to ignore
    IGNORE_DIRS = {
        'node_modules', '__pycache__', '.git', '.venv', 'venv',
        'dist', 'build', '.pytest_cache', 'coverage', '.mypy_cache'
    }
    
    def __init__(self, root_path: str):
        """
        Initialize analyzer for a repository.
        
        Args:
            root_path: Root directory of the repository to analyze
        """
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Path does not exist: {root_path}")
        
        # Initialize parsers
        self.parsers = {
            LanguageType.PYTHON: PythonParser(),
            LanguageType.JAVASCRIPT: JavaScriptParser(),
            LanguageType.TYPESCRIPT: TypeScriptParser(),
        }
        
        # Current graph
        self.graph: Optional[ShandorCode] = None
        
        logger.info(f"Initialized analyzer for {self.root_path}")
    
    def analyze(self) -> ShandorCode:
        """
        Analyze the entire repository.
        
        Returns:
            Complete code graph with all entities and dependencies
        """
        start_time = time.time()
        logger.info("Starting code analysis...")
        
        # Initialize new graph
        graph = ShandorCode(root_path=str(self.root_path))
        
        # Discover all code files
        files = self._discover_files()
        logger.info(f"Found {len(files)} code files")
        
        # Parse each file
        for file_path in files:
            try:
                lang = self._detect_language(file_path)
                if lang == LanguageType.UNKNOWN:
                    continue
                
                parser = self.parsers.get(lang)
                if not parser:
                    continue
                
                logger.debug(f"Parsing {file_path}")
                entities, dependencies = parser.parse_file(str(file_path))
                
                # Add to graph
                for entity in entities:
                    graph.add_entity(entity)
                
                for dependency in dependencies:
                    graph.add_dependency(dependency)
                
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}", exc_info=True)
        
        # Calculate aggregate metrics
        self._calculate_metrics(graph)
        
        # Store analysis duration
        duration_ms = int((time.time() - start_time) * 1000)
        graph.analysis_duration_ms = duration_ms
        
        self.graph = graph
        logger.info(
            f"Analysis complete: {graph.total_files} files, "
            f"{len(graph.entities)} entities, {len(graph.dependencies)} dependencies "
            f"in {duration_ms}ms"
        )
        
        return graph
    
    def check_boundaries(self, boundaries: List[ModuleBoundary]) -> List[BoundaryViolation]:
        """
        Check for violations of module boundary rules.
        
        Args:
            boundaries: List of module boundary definitions
            
        Returns:
            List of detected violations
        """
        if not self.graph:
            raise ValueError("Must run analyze() before checking boundaries")
        
        violations: List[BoundaryViolation] = []
        
        # Build module map (path prefix -> module name)
        module_map: Dict[str, ModuleBoundary] = {}
        for boundary in boundaries:
            module_map[boundary.path] = boundary
        
        # Check each dependency
        for dep in self.graph.dependencies:
            # Skip non-import dependencies for boundary checks
            if dep.type != DependencyType.IMPORT:
                continue
            
            source_entity = self.graph.get_entity(dep.source_id)
            target_entity = self.graph.get_entity(dep.target_id)
            
            if not source_entity or not target_entity:
                continue
            
            # Determine which modules the entities belong to
            source_module = self._find_module(source_entity.path, module_map)
            target_module = self._find_module(target_entity.path, module_map)
            
            if not source_module or not target_module:
                continue
            
            # Skip self-dependencies
            if source_module.name == target_module.name:
                continue
            
            # Check if dependency is allowed
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
                            f"'{target_module.name}' (violation at {source_entity.path}:"
                            f"{dep.line_number})"
                        ),
                    )
                )
        
        logger.info(f"Found {len(violations)} boundary violations")
        return violations
    
    def get_metrics(self) -> Dict[str, any]:
        """
        Get summary metrics for the codebase.
        
        Returns:
            Dictionary of metrics
        """
        if not self.graph:
            raise ValueError("Must run analyze() before getting metrics")
        
        return {
            'total_files': self.graph.total_files,
            'total_lines': self.graph.total_lines,
            'total_entities': len(self.graph.entities),
            'total_dependencies': len(self.graph.dependencies),
            'avg_complexity': self.graph.avg_complexity,
            'language_breakdown': dict(self.graph.language_breakdown),
            'analyzed_at': self.graph.analyzed_at.isoformat(),
            'analysis_duration_ms': self.graph.analysis_duration_ms,
        }
    
    def _discover_files(self) -> List[Path]:
        """
        Discover all code files in the repository.
        
        Returns:
            List of file paths to analyze
        """
        files: List[Path] = []
        
        for path in self.root_path.rglob('*'):
            # Skip directories
            if path.is_dir():
                continue
            
            # Skip ignored directories
            if any(ignored in path.parts for ignored in self.IGNORE_DIRS):
                continue
            
            # Check if it's a code file we can parse
            if path.suffix in self.LANGUAGE_MAP:
                files.append(path)
        
        return files
    
    def _detect_language(self, file_path: Path) -> LanguageType:
        """Detect programming language from file extension"""
        return self.LANGUAGE_MAP.get(file_path.suffix, LanguageType.UNKNOWN)
    
    def _calculate_metrics(self, graph: ShandorCode) -> None:
        """Calculate aggregate metrics for the graph"""
        total_complexity = 0
        complexity_count = 0
        total_lines = 0
        file_count = 0
        
        for entity in graph.entities.values():
            if entity.complexity:
                total_complexity += entity.complexity.cyclomatic_complexity
                complexity_count += 1
                total_lines += entity.complexity.lines_of_code
            
            if entity.type.value == 'file':
                file_count += 1
        
        graph.total_files = file_count
        graph.total_lines = total_lines
        graph.avg_complexity = (
            total_complexity / complexity_count if complexity_count > 0 else 0.0
        )
    
    def _find_module(
        self, file_path: str, module_map: Dict[str, ModuleBoundary]
    ) -> Optional[ModuleBoundary]:
        """Find which module a file belongs to based on path"""
        for path_prefix, module in module_map.items():
            if file_path.startswith(path_prefix):
                return module
        return None
