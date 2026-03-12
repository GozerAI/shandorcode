# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / 1450 Enterprises LLC

"""
Python code parser using tree-sitter.

Extracts code entities, dependencies, and metrics from Python files.
"""

import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Node

from ..core.models import (
    CodeEntity,
    EntityType,
    LanguageType,
    Dependency,
    DependencyType,
    ComplexityMetrics,
)


class PythonParser:
    """Parse Python code using tree-sitter"""
    
    def __init__(self):
        """Initialize Python parser"""
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)
        
    def parse_file(self, file_path: str) -> tuple[List[CodeEntity], List[Dependency]]:
        """
        Parse a Python file and extract entities and dependencies.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Tuple of (entities, dependencies)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            # Return empty if file can't be read
            return [], []
        
        tree = self.parser.parse(bytes(source_code, 'utf8'))
        
        entities: List[CodeEntity] = []
        dependencies: List[Dependency] = []
        
        # Create file entity
        file_id = self._generate_id(file_path)
        file_entity = CodeEntity(
            id=file_id,
            name=Path(file_path).name,
            type=EntityType.FILE,
            language=LanguageType.PYTHON,
            path=file_path,
            start_line=1,
            end_line=len(source_code.split('\n')),
            complexity=self._calculate_file_complexity(source_code),
        )
        entities.append(file_entity)
        
        # Extract entities from AST
        self._extract_entities(
            tree.root_node,
            source_code,
            file_path,
            file_id,
            entities,
            dependencies,
        )
        
        return entities, dependencies
    
    def _extract_entities(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        parent_id: str,
        entities: List[CodeEntity],
        dependencies: List[Dependency],
    ) -> None:
        """Recursively extract entities from AST nodes"""
        
        # Extract class definitions
        if node.type == 'class_definition':
            self._extract_class(node, source_code, file_path, parent_id, entities, dependencies)
        
        # Extract function definitions
        elif node.type == 'function_definition':
            self._extract_function(node, source_code, file_path, parent_id, entities, dependencies)
        
        # Extract imports
        elif node.type in ('import_statement', 'import_from_statement'):
            self._extract_import(node, source_code, parent_id, dependencies)
        
        # Recurse into children
        for child in node.children:
            self._extract_entities(child, source_code, file_path, parent_id, entities, dependencies)
    
    def _extract_class(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        parent_id: str,
        entities: List[CodeEntity],
        dependencies: List[Dependency],
    ) -> None:
        """Extract class entity and its methods"""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return
        
        class_name = source_code[name_node.start_byte:name_node.end_byte]
        class_id = self._generate_id(f"{file_path}::{class_name}")
        
        # Extract docstring
        docstring = self._extract_docstring(node, source_code)
        
        # Calculate complexity
        class_code = source_code[node.start_byte:node.end_byte]
        complexity = self._calculate_complexity(class_code)
        
        class_entity = CodeEntity(
            id=class_id,
            name=class_name,
            type=EntityType.CLASS,
            language=LanguageType.PYTHON,
            path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_id,
            complexity=complexity,
            docstring=docstring,
        )
        entities.append(class_entity)
        
        # Extract base classes (inheritance)
        bases_node = node.child_by_field_name('superclasses')
        if bases_node:
            for base in bases_node.children:
                if base.type == 'identifier':
                    base_name = source_code[base.start_byte:base.end_byte]
                    base_id = self._generate_id(f"{file_path}::{base_name}")
                    dependencies.append(
                        Dependency(
                            source_id=class_id,
                            target_id=base_id,
                            type=DependencyType.INHERITANCE,
                            line_number=base.start_point[0] + 1,
                        )
                    )
        
        # Extract methods
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                if child.type == 'function_definition':
                    self._extract_function(
                        child, source_code, file_path, class_id, entities, dependencies
                    )
    
    def _extract_function(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        parent_id: str,
        entities: List[CodeEntity],
        dependencies: List[Dependency],
    ) -> None:
        """Extract function/method entity"""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return
        
        func_name = source_code[name_node.start_byte:name_node.end_byte]
        func_id = self._generate_id(f"{parent_id}::{func_name}")
        
        # Determine if it's a method or function
        parent_entity = next((e for e in entities if e.id == parent_id), None)
        entity_type = EntityType.METHOD if parent_entity and parent_entity.type == EntityType.CLASS else EntityType.FUNCTION
        
        # Extract docstring
        docstring = self._extract_docstring(node, source_code)
        
        # Calculate complexity
        func_code = source_code[node.start_byte:node.end_byte]
        complexity = self._calculate_complexity(func_code)
        
        func_entity = CodeEntity(
            id=func_id,
            name=func_name,
            type=entity_type,
            language=LanguageType.PYTHON,
            path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_id,
            complexity=complexity,
            docstring=docstring,
        )
        entities.append(func_entity)
        
        # Extract function calls within the body
        body = node.child_by_field_name('body')
        if body:
            self._extract_calls(body, source_code, func_id, dependencies)
    
    def _extract_import(
        self,
        node: Node,
        source_code: str,
        parent_id: str,
        dependencies: List[Dependency],
    ) -> None:
        """Extract import dependencies"""
        if node.type == 'import_statement':
            # import module
            for child in node.children:
                if child.type == 'dotted_name':
                    module_name = source_code[child.start_byte:child.end_byte]
                    target_id = self._generate_id(f"module::{module_name}")
                    dependencies.append(
                        Dependency(
                            source_id=parent_id,
                            target_id=target_id,
                            type=DependencyType.IMPORT,
                            line_number=node.start_point[0] + 1,
                        )
                    )
        
        elif node.type == 'import_from_statement':
            # from module import ...
            module_node = node.child_by_field_name('module_name')
            if module_node:
                module_name = source_code[module_node.start_byte:module_node.end_byte]
                target_id = self._generate_id(f"module::{module_name}")
                dependencies.append(
                    Dependency(
                        source_id=parent_id,
                        target_id=target_id,
                        type=DependencyType.IMPORT,
                        line_number=node.start_point[0] + 1,
                    )
                )
    
    def _extract_calls(
        self,
        node: Node,
        source_code: str,
        parent_id: str,
        dependencies: List[Dependency],
    ) -> None:
        """Extract function call dependencies"""
        if node.type == 'call':
            func_node = node.child_by_field_name('function')
            if func_node:
                if func_node.type == 'identifier':
                    func_name = source_code[func_node.start_byte:func_node.end_byte]
                    target_id = self._generate_id(f"function::{func_name}")
                    dependencies.append(
                        Dependency(
                            source_id=parent_id,
                            target_id=target_id,
                            type=DependencyType.CALL,
                            line_number=node.start_point[0] + 1,
                        )
                    )
        
        # Recurse
        for child in node.children:
            self._extract_calls(child, source_code, parent_id, dependencies)
    
    def _extract_docstring(self, node: Node, source_code: str) -> Optional[str]:
        """Extract docstring from a class or function"""
        body = node.child_by_field_name('body')
        if not body or not body.children:
            return None
        
        # First statement in body might be docstring
        first_stmt = body.children[0]
        if first_stmt.type == 'expression_statement':
            expr = first_stmt.children[0] if first_stmt.children else None
            if expr and expr.type == 'string':
                docstring = source_code[expr.start_byte:expr.end_byte]
                # Remove quotes
                return docstring.strip('"\'')
        
        return None
    
    def _calculate_complexity(self, code: str) -> ComplexityMetrics:
        """Calculate complexity metrics for code"""
        lines = code.split('\n')
        total_lines = len(lines)
        
        # Count logical lines (non-empty, non-comment)
        logical_lines = sum(
            1 for line in lines
            if line.strip() and not line.strip().startswith('#')
        )
        
        # Count comment lines
        comment_lines = sum(
            1 for line in lines
            if line.strip().startswith('#')
        )
        
        # Simple cyclomatic complexity (count decision points)
        decision_keywords = ['if', 'elif', 'else', 'for', 'while', 'except', 'and', 'or']
        cyclomatic = 1  # Base complexity
        for keyword in decision_keywords:
            cyclomatic += code.count(f' {keyword} ') + code.count(f'\n{keyword} ')
        
        return ComplexityMetrics(
            cyclomatic_complexity=cyclomatic,
            lines_of_code=total_lines,
            logical_lines=logical_lines,
            comment_lines=comment_lines,
        )
    
    def _calculate_file_complexity(self, code: str) -> ComplexityMetrics:
        """Calculate overall file complexity"""
        return self._calculate_complexity(code)
    
    def _generate_id(self, identifier: str) -> str:
        """Generate a unique ID for an entity"""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]
