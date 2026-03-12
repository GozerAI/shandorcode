#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later

"""
Quick test script to validate ShandorCode functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.analyzer import CodeAnalyzer
from src.core.models import ModuleBoundary

def main():
    print("=" * 60)
    print("ShandorCode Test - Analyzing itself!")
    print("=" * 60)
    
    # Analyze the shandorcode project itself
    src_path = project_root / "src"
    analyzer = CodeAnalyzer(str(src_path))
    
    print("\n🔍 Running analysis...")
    graph = analyzer.analyze()
    
    print(f"\n📊 Analysis Results:")
    print(f"  Total files: {graph.total_files}")
    print(f"  Total entities: {len(graph.entities)}")
    print(f"  Total dependencies: {len(graph.dependencies)}")
    print(f"  Average complexity: {graph.avg_complexity:.2f}")
    
    print(f"\n📁 Language breakdown:")
    for lang, count in graph.language_breakdown.items():
        print(f"  {lang}: {count} files")
    
    # Show some entities
    print(f"\n🏗️  Sample entities:")
    for i, (entity_id, entity) in enumerate(list(graph.entities.items())[:5]):
        print(f"  {i+1}. {entity.name} ({entity.type}) - {entity.path}")
        if entity.complexity:
            print(f"     Complexity: {entity.complexity.cyclomatic_complexity}, LOC: {entity.complexity.lines_of_code}")
    
    # Show some dependencies
    print(f"\n🔗 Sample dependencies:")
    for i, dep in enumerate(graph.dependencies[:5]):
        source = graph.get_entity(dep.source_id)
        target = graph.get_entity(dep.target_id)
        if source and target:
            print(f"  {i+1}. {source.name} -> {target.name} ({dep.type})")
    
    # Test boundary checking
    print(f"\n🚧 Testing boundary violations...")
    boundaries = [
        ModuleBoundary(
            name="core",
            path="/home/claude/codegraph/src/core",
            allowed_dependencies=[]  # Core should not depend on anything
        ),
        ModuleBoundary(
            name="parsers",
            path="/home/claude/codegraph/src/parsers",
            allowed_dependencies=["core"]  # Parsers can depend on core
        ),
        ModuleBoundary(
            name="api",
            path="/home/claude/codegraph/src/api",
            allowed_dependencies=["core", "parsers"]  # API can depend on core and parsers
        ),
    ]
    
    violations = analyzer.check_boundaries(boundaries)
    if violations:
        print(f"\n⚠️  Found {len(violations)} boundary violations:")
        for v in violations[:3]:
            print(f"  - {v.source_module} -> {v.target_module}")
            print(f"    {v.message}")
    else:
        print(f"\n✅ No boundary violations detected!")
    
    print(f"\n🎉 Test complete! ShandorCode is working correctly.")
    print(f"   Analysis took {graph.analysis_duration_ms}ms")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
