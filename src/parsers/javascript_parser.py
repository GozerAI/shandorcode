# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / GozerAI

"""
JavaScript and TypeScript parser using tree-sitter.

Extracts code entities, dependencies, and metrics from JS/TS files.
"""

import hashlib
from pathlib import Path
from typing import List, Optional
import tree_sitter_javascript as tsjs
import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser, Node

from ..core.models import (
    CodeEntity,
    EntityType,
    LanguageType,
    Dependency,
    DependencyType,
    ComplexityMetrics,
)


class JavaScriptParser:
    """Parse JavaScript code using tree-sitter"""
    
    def __init__(self):
        """Initialize JavaScript parser"""
        self.language = Language(tsjs.language())
        self.parser = Parser(self.language)
    
    def parse_file(self, file_path: str) -> tuple[List[CodeEntity], List[Dependency]]:
        """Parse a JavaScript file"""
        return self._parse(file_path, LanguageType.JAVASCRIPT)
    
    def _parse(
        self, file_path: str, lang_type: LanguageType
    ) -> tuple[List[CodeEntity], List[Dependency]]:
        """Internal parse implementation"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception:
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
            language=lang_type,
            path=file_path,
            start_line=1,
            end_line=len(source_code.split('\n')),
            complexity=self._calculate_file_complexity(source_code),
        )
        entities.append(file_entity)
        
        # Extract entities
        self._extract_entities(
            tree.root_node,
            source_code,
            file_path,
            file_id,
            lang_type,
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
        lang_type: LanguageType,
        entities: List[CodeEntity],
        dependencies: List[Dependency],
    ) -> None:
        """Recursively extract entities from AST"""
        
        # Extract classes
        if node.type in ('class_declaration', 'class'):
            self._extract_class(node, source_code, file_path, parent_id, lang_type, entities, dependencies)
        
        # Extract functions
        elif node.type in ('function_declaration', 'function', 'arrow_function', 'method_definition'):
            self._extract_function(node, source_code, file_path, parent_id, lang_type, entities, dependencies)
        
        # Extract imports
        elif node.type in ('import_statement', 'import_clause'):
            self._extract_import(node, source_code, parent_id, dependencies)
        
        # Recurse
        for child in node.children:
            self._extract_entities(child, source_code, file_path, parent_id, lang_type, entities, dependencies)
    
    def _extract_class(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        parent_id: str,
        lang_type: LanguageType,
        entities: List[CodeEntity],
        dependencies: List[Dependency],
    ) -> None:
        """Extract class entity"""
        name_node = node.child_by_field_name('name')
        if not name_node:
            return
        
        class_name = source_code[name_node.start_byte:name_node.end_byte]
        class_id = self._generate_id(f"{file_path}::{class_name}")
        
        class_code = source_code[node.start_byte:node.end_byte]
        complexity = self._calculate_complexity(class_code)
        
        class_entity = CodeEntity(
            id=class_id,
            name=class_name,
            type=EntityType.CLASS,
            language=lang_type,
            path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_id,
            complexity=complexity,
        )
        entities.append(class_entity)
        
        # Extract methods from class body
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                if child.type in ('method_definition', 'field_definition'):
                    self._extract_function(
                        child, source_code, file_path, class_id, lang_type, entities, dependencies
                    )
    
    def _extract_function(
        self,
        node: Node,
        source_code: str,
        file_path: str,
        parent_id: str,
        lang_type: LanguageType,
        entities: List[CodeEntity],
        dependencies: List[Dependency],
    ) -> None:
        """Extract function entity"""
        # Get function name
        name_node = node.child_by_field_name('name')
        if not name_node:
            # Arrow functions might not have names
            func_name = '<anonymous>'
        else:
            func_name = source_code[name_node.start_byte:name_node.end_byte]
        
        func_id = self._generate_id(f"{parent_id}::{func_name}")
        
        # Determine entity type
        parent_entity = next((e for e in entities if e.id == parent_id), None)
        entity_type = EntityType.METHOD if parent_entity and parent_entity.type == EntityType.CLASS else EntityType.FUNCTION
        
        func_code = source_code[node.start_byte:node.end_byte]
        complexity = self._calculate_complexity(func_code)
        
        func_entity = CodeEntity(
            id=func_id,
            name=func_name,
            type=entity_type,
            language=lang_type,
            path=file_path,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            parent=parent_id,
            complexity=complexity,
        )
        entities.append(func_entity)
        
        # Extract calls from body
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
        # Find import source
        source_node = node.child_by_field_name('source')
        if source_node:
            import_path = source_code[source_node.start_byte:source_node.end_byte]
            # Remove quotes
            import_path = import_path.strip('"\'')
            target_id = self._generate_id(f"module::{import_path}")
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
        if node.type == 'call_expression':
            func_node = node.child_by_field_name('function')
            if func_node and func_node.type == 'identifier':
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
        
        for child in node.children:
            self._extract_calls(child, source_code, parent_id, dependencies)
    
    def _calculate_complexity(self, code: str) -> ComplexityMetrics:
        """Calculate complexity metrics"""
        lines = code.split('\n')
        total_lines = len(lines)
        
        logical_lines = sum(
            1 for line in lines
            if line.strip() and not line.strip().startswith('//')
        )
        
        comment_lines = sum(
            1 for line in lines
            if line.strip().startswith('//')
        )
        
        # Count decision points
        decision_keywords = ['if', 'else', 'for', 'while', 'case', '&&', '||', '?']
        cyclomatic = 1
        for keyword in decision_keywords:
            cyclomatic += code.count(keyword)
        
        return ComplexityMetrics(
            cyclomatic_complexity=min(cyclomatic, 50),  # Cap at reasonable value
            lines_of_code=total_lines,
            logical_lines=logical_lines,
            comment_lines=comment_lines,
        )
    
    def _calculate_file_complexity(self, code: str) -> ComplexityMetrics:
        """Calculate file complexity"""
        return self._calculate_complexity(code)
    
    def _generate_id(self, identifier: str) -> str:
        """Generate unique ID"""
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]


class TypeScriptParser(JavaScriptParser):
    """Parse TypeScript code using tree-sitter"""
    
    def __init__(self):
        """Initialize TypeScript parser"""
        # Use TypeScript language
        self.language = Language(tsts.language_typescript())
        self.parser = Parser(self.language)
    
    def parse_file(self, file_path: str) -> tuple[List[CodeEntity], List[Dependency]]:
        """Parse a TypeScript file"""
        return self._parse(file_path, LanguageType.TYPESCRIPT)
