#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Example: Using ShandorCode to analyze a GozerAI ecosystem project.

This demonstrates how ShandorCode can help maintain clean architecture
in your modular GozerAI ecosystem (Plugin-SDK, Vinzy-Engine, Zuultimate).
"""

import sys
sys.path.insert(0, '/home/claude/codegraph')

from src.core.analyzer import CodeAnalyzer
from src.core.models import ModuleBoundary

def analyze_gozerai_project(project_path: str):
    """
    Analyze a GozerAI ecosystem project with strict architectural boundaries.
    
    This enforces the modular philosophy: core components have zero dependencies,
    upper layers depend only on lower layers, and plugins are completely isolated.
    """
    
    print(f"\n{'='*70}")
    print(f"ShandorCode Analysis: GozerAI Ecosystem Project")
    print(f"{'='*70}\n")
    
    # Initialize analyzer
    print(f"📂 Analyzing: {project_path}")
    analyzer = CodeAnalyzer(project_path)
    
    # Run analysis
    print("🔍 Running code analysis...")
    graph = analyzer.analyze()
    
    # Display results
    print(f"\n📊 Analysis Results:")
    print(f"  ├─ Total Files: {graph.total_files}")
    print(f"  ├─ Total Entities: {len(graph.entities)}")
    print(f"  ├─ Total Dependencies: {len(graph.dependencies)}")
    print(f"  ├─ Average Complexity: {graph.avg_complexity:.2f}")
    print(f"  └─ Analysis Time: {graph.analysis_duration_ms}ms")
    
    print(f"\n📁 Language Breakdown:")
    for lang, count in graph.language_breakdown.items():
        print(f"  ├─ {lang}: {count} entities")
    
    # Define GozerAI architectural boundaries
    # This enforces your modular philosophy:
    # - Core has no dependencies
    # - Plugins can depend on core only
    # - API can depend on core and plugins
    # - Utils is standalone
    
    boundaries = [
        ModuleBoundary(
            name="core",
            path=f"{project_path}/src/core",
            allowed_dependencies=[],
            description="Core business logic - zero external dependencies"
        ),
        ModuleBoundary(
            name="plugins",
            path=f"{project_path}/src/plugins",
            allowed_dependencies=["core"],
            description="Plugin system - can only depend on core"
        ),
        ModuleBoundary(
            name="api",
            path=f"{project_path}/src/api",
            allowed_dependencies=["core", "plugins"],
            description="API layer - orchestrates core and plugins"
        ),
        ModuleBoundary(
            name="utils",
            path=f"{project_path}/src/utils",
            allowed_dependencies=[],
            description="Utility functions - standalone helpers"
        ),
    ]
    
    # Check architectural boundaries
    print(f"\n🏗️  Checking Architectural Boundaries...")
    print(f"  Enforcing modular isolation principles...")
    
    violations = analyzer.check_boundaries(boundaries)
    
    if violations:
        print(f"\n⚠️  Found {len(violations)} Architecture Violations:")
        print(f"  {'─'*66}")
        
        for i, v in enumerate(violations, 1):
            severity_symbol = {
                'error': '❌',
                'warning': '⚠️',
                'info': 'ℹ️'
            }.get(v.severity, '•')
            
            print(f"\n  {severity_symbol} Violation #{i}: {v.severity.upper()}")
            print(f"     Module: {v.source_module} ──> {v.target_module}")
            print(f"     Entity: {v.source_entity} → {v.target_entity}")
            print(f"     Type: {v.dependency_type}")
            print(f"     Issue: {v.message}")
        
        print(f"\n  💡 Recommendation:")
        print(f"     Review and refactor these dependencies to maintain clean")
        print(f"     architectural boundaries. Consider:")
        print(f"     - Moving shared logic to core")
        print(f"     - Using dependency injection")
        print(f"     - Creating proper abstractions")
        
    else:
        print(f"\n✅ No Architecture Violations Detected!")
        print(f"   Your modular architecture is clean and properly isolated.")
    
    # Identify complexity hotspots
    print(f"\n🔥 Complexity Hotspots (Top 5):")
    entities_by_complexity = sorted(
        [e for e in graph.entities.values() if e.complexity],
        key=lambda e: e.complexity.cyclomatic_complexity,
        reverse=True
    )[:5]
    
    for i, entity in enumerate(entities_by_complexity, 1):
        complexity = entity.complexity.cyclomatic_complexity
        loc = entity.complexity.lines_of_code
        
        # Color code by severity
        if complexity > 20:
            symbol = '🔴'
        elif complexity > 10:
            symbol = '🟡'
        else:
            symbol = '🟢'
        
        print(f"  {symbol} #{i}. {entity.name}")
        print(f"     Complexity: {complexity}, LOC: {loc}")
        print(f"     Path: {entity.path}:{entity.start_line}")
    
    # Module coupling analysis
    print(f"\n🔗 Module Coupling Analysis:")
    
    module_deps = {}
    for dep in graph.dependencies:
        source_entity = graph.get_entity(dep.source_id)
        target_entity = graph.get_entity(dep.target_id)
        
        if source_entity and target_entity:
            # Extract module from path
            source_module = extract_module(source_entity.path, project_path)
            target_module = extract_module(target_entity.path, project_path)
            
            if source_module != target_module:
                key = f"{source_module} -> {target_module}"
                module_deps[key] = module_deps.get(key, 0) + 1
    
    if module_deps:
        print(f"  Cross-module dependencies:")
        for coupling, count in sorted(module_deps.items(), key=lambda x: -x[1])[:5]:
            print(f"  ├─ {coupling}: {count} dependencies")
    else:
        print(f"  ✨ Perfect isolation - no cross-module dependencies!")
    
    # Summary and recommendations
    print(f"\n{'='*70}")
    print(f"Summary & Recommendations")
    print(f"{'='*70}\n")
    
    # Architecture health score
    violation_score = max(0, 100 - (len(violations) * 10))
    complexity_score = max(0, 100 - (graph.avg_complexity - 5) * 10)
    health_score = (violation_score + complexity_score) / 2
    
    print(f"🎯 Architecture Health Score: {health_score:.1f}/100")
    
    if health_score >= 90:
        print(f"   Excellent! Your architecture is clean and maintainable.")
    elif health_score >= 70:
        print(f"   Good, but there's room for improvement.")
    else:
        print(f"   Needs attention. Focus on reducing violations and complexity.")
    
    print(f"\n📋 Action Items:")
    
    if violations:
        print(f"  1. ⚠️  Address {len(violations)} architectural violations")
    
    if graph.avg_complexity > 10:
        print(f"  2. 📉 Reduce average complexity from {graph.avg_complexity:.1f} to <10")
    
    if graph.total_files > 100:
        print(f"  3. 📦 Consider splitting into smaller modules")
    
    if not violations and graph.avg_complexity < 10:
        print(f"  ✅ Keep up the excellent work! Your codebase is well-structured.")
    
    print(f"\n💡 Next Steps:")
    print(f"  • Run ShandorCode in watch mode during development")
    print(f"  • Add pre-commit hooks for architecture validation")
    print(f"  • Set up CI/CD pipeline checks")
    print(f"  • Review complexity hotspots for refactoring opportunities")
    
    print(f"\n{'='*70}\n")

def extract_module(file_path: str, project_path: str) -> str:
    """Extract module name from file path"""
    relative = file_path.replace(project_path, '').lstrip('/')
    parts = relative.split('/')
    
    if len(parts) >= 3 and parts[0] == 'src':
        return parts[1]  # e.g., 'core', 'plugins', 'api'
    
    return 'unknown'

if __name__ == "__main__":
    # Example usage
    # In reality, you'd pass the path to your actual GozerAI project
    
    if len(sys.argv) > 1:
        project_path = sys.argv[1]
    else:
        # Analyze ShandorCode itself as an example
        project_path = "/home/claude/codegraph/src"
        print(f"\n💡 No project path provided. Analyzing ShandorCode itself as example.")
        print(f"   Usage: python example_gozerai_analysis.py /path/to/your/project")
    
    analyze_gozerai_project(project_path)
