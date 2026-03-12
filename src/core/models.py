# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2024 Chris Arseno / 1450 Enterprises LLC

"""
Core data models for ShandorCode.

Defines the structure for code entities, dependencies, metrics, and graphs.
"""

from typing import Dict, List, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class LanguageType(str, Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Types of code entities"""
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"


class DependencyType(str, Enum):
    """Types of dependencies between entities"""
    IMPORT = "import"
    CALL = "call"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"


class ComplexityMetrics(BaseModel):
    """Code complexity metrics"""
    cyclomatic_complexity: int = Field(ge=1, description="Cyclomatic complexity (McCabe)")
    cognitive_complexity: Optional[int] = Field(None, ge=0)
    lines_of_code: int = Field(ge=0, description="Physical lines of code")
    logical_lines: int = Field(ge=0, description="Logical lines of code")
    comment_lines: int = Field(ge=0, description="Comment lines")
    maintainability_index: Optional[float] = Field(None, ge=0, le=100)


class CodeEntity(BaseModel):
    """Represents a code entity (file, class, function, etc.)"""
    id: str = Field(description="Unique identifier")
    name: str = Field(description="Entity name")
    type: EntityType
    language: LanguageType
    path: str = Field(description="File path")
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    complexity: Optional[ComplexityMetrics] = None
    docstring: Optional[str] = None
    
    # Relationships
    children: List[str] = Field(default_factory=list, description="Child entity IDs")
    parent: Optional[str] = Field(None, description="Parent entity ID")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Dependency(BaseModel):
    """Represents a dependency between code entities"""
    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    type: DependencyType
    weight: int = Field(default=1, ge=1, description="Dependency strength")
    line_number: Optional[int] = Field(None, ge=1)


class ModuleBoundary(BaseModel):
    """Defines architectural module boundaries"""
    name: str
    path: str
    allowed_dependencies: List[str] = Field(
        default_factory=list,
        description="List of module names this module can depend on"
    )
    description: Optional[str] = None


class BoundaryViolation(BaseModel):
    """Represents a violation of module boundaries"""
    source_module: str
    target_module: str
    source_entity: str
    target_entity: str
    dependency_type: DependencyType
    severity: str = Field(default="warning", pattern="^(info|warning|error)$")
    message: str


class ShandorCode(BaseModel):
    """Complete code graph with entities and dependencies"""
    entities: Dict[str, CodeEntity] = Field(default_factory=dict)
    dependencies: List[Dependency] = Field(default_factory=list)
    root_path: str
    language_breakdown: Dict[LanguageType, int] = Field(default_factory=dict)
    
    # Computed metrics
    total_files: int = 0
    total_lines: int = 0
    avg_complexity: float = 0.0
    
    # Analysis metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    analysis_duration_ms: Optional[int] = None
    
    def add_entity(self, entity: CodeEntity) -> None:
        """Add an entity to the graph"""
        self.entities[entity.id] = entity
        self.language_breakdown[entity.language] = (
            self.language_breakdown.get(entity.language, 0) + 1
        )
    
    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency to the graph"""
        self.dependencies.append(dependency)
    
    def get_entity(self, entity_id: str) -> Optional[CodeEntity]:
        """Get an entity by ID"""
        return self.entities.get(entity_id)
    
    def get_dependencies_for(self, entity_id: str) -> List[Dependency]:
        """Get all dependencies for an entity"""
        return [
            dep for dep in self.dependencies
            if dep.source_id == entity_id
        ]
    
    def get_dependents_of(self, entity_id: str) -> List[Dependency]:
        """Get all entities that depend on this entity"""
        return [
            dep for dep in self.dependencies
            if dep.target_id == entity_id
        ]

    def to_dict(self) -> dict:
        """Convert to dictionary (compatibility method for Pydantic v2)"""
        return self.model_dump(mode='json')


class AnalysisChange(BaseModel):
    """Represents a change in analysis results"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    changed_files: List[str] = Field(default_factory=list)
    added_entities: List[str] = Field(default_factory=list)
    removed_entities: List[str] = Field(default_factory=list)
    modified_entities: List[str] = Field(default_factory=list)
    new_dependencies: List[Dependency] = Field(default_factory=list)
    removed_dependencies: List[Dependency] = Field(default_factory=list)
    
    # Impact analysis
    affected_modules: Set[str] = Field(default_factory=set)
    boundary_violations: List[BoundaryViolation] = Field(default_factory=list)
