# ShandorCode Usage Guide

## Quick Start

### 1. Start the Server

```bash
# Analyze current directory
./start.sh

# Analyze specific repository
./start.sh /path/to/your/repo

# Custom host/port
HOST=0.0.0.0 PORT=8080 ./start.sh /path/to/repo
```

### 2. Open Visualization

Navigate to `http://localhost:8765` in your browser.

You'll see:
- **Header**: Summary statistics (files, entities, dependencies, complexity)
- **Sidebar**: View controls and entity details
- **Main View**: Interactive force-directed graph
- **Status**: WebSocket connection indicator

### 3. Interact with the Graph

- **Drag nodes** to rearrange the layout
- **Click nodes** to see entity details
- **Toggle dependencies** to show/hide connections
- **Reset view** to restore default layout

## Programmatic Usage

### Basic Analysis

```python
from src.core.analyzer import CodeAnalyzer

# Initialize analyzer
analyzer = CodeAnalyzer("/path/to/repository")

# Run analysis
graph = analyzer.analyze()

# Access results
print(f"Files: {graph.total_files}")
print(f"Entities: {len(graph.entities)}")
print(f"Dependencies: {len(graph.dependencies)}")
print(f"Avg Complexity: {graph.avg_complexity:.2f}")

# Language breakdown
for lang, count in graph.language_breakdown.items():
    print(f"{lang}: {count}")
```

### Get Metrics

```python
# Get summary metrics
metrics = analyzer.get_metrics()

print(metrics)
# {
#     'total_files': 42,
#     'total_lines': 3250,
#     'total_entities': 187,
#     'total_dependencies': 245,
#     'avg_complexity': 5.3,
#     'language_breakdown': {...},
#     'analyzed_at': '2024-12-14T...',
#     'analysis_duration_ms': 145
# }
```

### Entity Inspection

```python
# Get specific entity
entity_id = list(graph.entities.keys())[0]
entity = graph.get_entity(entity_id)

print(f"Name: {entity.name}")
print(f"Type: {entity.type}")
print(f"Path: {entity.path}")
print(f"Lines: {entity.start_line}-{entity.end_line}")

# Check complexity
if entity.complexity:
    print(f"Cyclomatic Complexity: {entity.complexity.cyclomatic_complexity}")
    print(f"LOC: {entity.complexity.lines_of_code}")
    print(f"Logical Lines: {entity.complexity.logical_lines}")
```

### Dependency Analysis

```python
# Get dependencies for an entity
deps = graph.get_dependencies_for(entity_id)
for dep in deps:
    target = graph.get_entity(dep.target_id)
    print(f"{entity.name} -> {target.name} ({dep.type})")

# Get dependents (who depends on this entity)
dependents = graph.get_dependents_of(entity_id)
for dep in dependents:
    source = graph.get_entity(dep.source_id)
    print(f"{source.name} depends on {entity.name}")
```

## Architecture Validation

### Define Module Boundaries

```python
from src.core.models import ModuleBoundary

boundaries = [
    ModuleBoundary(
        name="core",
        path="/path/to/repo/src/core",
        allowed_dependencies=[],  # Core should not depend on anything
        description="Core business logic"
    ),
    ModuleBoundary(
        name="api",
        path="/path/to/repo/src/api",
        allowed_dependencies=["core"],
        description="API layer can depend on core"
    ),
    ModuleBoundary(
        name="ui",
        path="/path/to/repo/src/ui",
        allowed_dependencies=["api", "core"],
        description="UI can depend on API and core"
    ),
]
```

### Check for Violations

```python
# Run boundary check
violations = analyzer.check_boundaries(boundaries)

if violations:
    print(f"⚠️  Found {len(violations)} violations:")
    for v in violations:
        print(f"\n{v.severity.upper()}: {v.message}")
        print(f"  Module: {v.source_module} -> {v.target_module}")
        print(f"  Entity: {v.source_entity} -> {v.target_entity}")
        print(f"  Type: {v.dependency_type}")
else:
    print("✅ No architecture violations!")
```

### Example: Enforce Layered Architecture

```python
# Define strict layered architecture
layers = [
    ModuleBoundary(
        name="domain",
        path="src/domain",
        allowed_dependencies=[],
    ),
    ModuleBoundary(
        name="application",
        path="src/application",
        allowed_dependencies=["domain"],
    ),
    ModuleBoundary(
        name="infrastructure",
        path="src/infrastructure",
        allowed_dependencies=["domain", "application"],
    ),
    ModuleBoundary(
        name="presentation",
        path="src/presentation",
        allowed_dependencies=["application", "domain"],
    ),
]

violations = analyzer.check_boundaries(layers)

# This would catch violations like:
# - domain depending on application (wrong direction)
# - presentation directly accessing infrastructure (bypassing application layer)
```

## Real-time Monitoring

### File Watcher

```python
from src.core.watcher import FileWatcher

def handle_changes(changed_files):
    print(f"Files changed: {changed_files}")
    
    # Re-analyze
    graph = analyzer.analyze()
    
    # Check if changes introduced violations
    violations = analyzer.check_boundaries(boundaries)
    if violations:
        print("⚠️  New violations introduced!")
        for v in violations:
            print(f"  - {v.message}")

# Start watching
watcher = FileWatcher(
    "/path/to/repo",
    callback=handle_changes,
    debounce_seconds=1.0,  # Wait 1s before processing
)

# Run (blocks)
watcher.start()

# Or use as context manager
with FileWatcher("/path/to/repo", handle_changes) as watcher:
    # watcher is active
    pass
```

### Integration with Development Workflow

```python
# Example: Pre-commit hook
import sys

def pre_commit_check():
    analyzer = CodeAnalyzer(".")
    graph = analyzer.analyze()
    
    # Define boundaries
    boundaries = [...] # your boundaries
    
    # Check violations
    violations = analyzer.check_boundaries(boundaries)
    
    if violations:
        print("❌ Architecture violations detected!")
        for v in violations:
            print(f"  {v.message}")
        return 1
    
    # Check complexity threshold
    if graph.avg_complexity > 10:
        print(f"⚠️  Average complexity too high: {graph.avg_complexity:.1f}")
        return 1
    
    print("✅ All checks passed!")
    return 0

if __name__ == "__main__":
    sys.exit(pre_commit_check())
```

## API Usage

### REST API

```bash
# Analyze repository
curl -X POST http://localhost:8765/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/repo"}'

# Get metrics
curl http://localhost:8765/api/metrics

# Get graph
curl http://localhost:8765/api/graph

# Check boundaries
curl -X POST http://localhost:8765/api/check-boundaries \
  -H "Content-Type: application/json" \
  -d '{
    "boundaries": [
      {
        "name": "core",
        "path": "/path/to/repo/src/core",
        "allowed_dependencies": []
      }
    ]
  }'
```

### WebSocket Connection

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8765/ws');

ws.onopen = () => {
    console.log('Connected to ShandorCode');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'initial') {
        // Initial graph
        console.log('Initial graph received');
        renderGraph(data.graph);
    } else if (data.type === 'update') {
        // Live update
        console.log('Graph updated');
        updateGraph(data.graph);
    }
};

// Keep connection alive
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
    }
}, 30000);
```

## Advanced Use Cases

### 1. Multi-Repository Analysis

```python
repos = [
    "/path/to/repo1",
    "/path/to/repo2",
    "/path/to/repo3",
]

results = {}
for repo in repos:
    analyzer = CodeAnalyzer(repo)
    graph = analyzer.analyze()
    results[repo] = {
        'files': graph.total_files,
        'complexity': graph.avg_complexity,
        'violations': len(analyzer.check_boundaries(boundaries))
    }

# Compare results
for repo, metrics in results.items():
    print(f"{repo}: {metrics}")
```

### 2. Complexity Trend Analysis

```python
import json
from datetime import datetime

# Run analysis and save
analyzer = CodeAnalyzer("/path/to/repo")
graph = analyzer.analyze()

snapshot = {
    'timestamp': datetime.utcnow().isoformat(),
    'metrics': analyzer.get_metrics(),
}

# Append to history
with open('complexity_history.jsonl', 'a') as f:
    f.write(json.dumps(snapshot) + '\n')

# Later: analyze trends
# Track complexity over time, identify problematic files, etc.
```

### 3. Custom Metrics

```python
# Calculate custom metrics from graph

# 1. Find most complex entities
entities_by_complexity = sorted(
    graph.entities.values(),
    key=lambda e: e.complexity.cyclomatic_complexity if e.complexity else 0,
    reverse=True
)

print("Top 10 most complex entities:")
for i, entity in enumerate(entities_by_complexity[:10], 1):
    if entity.complexity:
        print(f"{i}. {entity.name}: {entity.complexity.cyclomatic_complexity}")

# 2. Find most connected entities (dependency analysis)
dependency_counts = {}
for dep in graph.dependencies:
    dependency_counts[dep.source_id] = dependency_counts.get(dep.source_id, 0) + 1

most_connected = sorted(
    dependency_counts.items(),
    key=lambda x: x[1],
    reverse=True
)[:10]

print("\nMost connected entities:")
for entity_id, count in most_connected:
    entity = graph.get_entity(entity_id)
    print(f"{entity.name}: {count} dependencies")

# 3. Calculate module cohesion
# (percentage of dependencies within same module vs external)
```

### 4. CI/CD Integration

```yaml
# .github/workflows/architecture-check.yml
name: Architecture Validation

on: [pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install ShandorCode
        run: |
          pip install -e .
      
      - name: Run Architecture Check
        run: |
          python scripts/check_architecture.py
```

## Tips and Best Practices

1. **Start Small**: Analyze a single module before entire repository
2. **Define Boundaries Early**: Set architectural rules from the start
3. **Monitor Complexity**: Track average complexity over time
4. **Review Violations**: Fix architecture violations immediately
5. **Use Pre-commit Hooks**: Prevent violations before they're committed
6. **Document Decisions**: Use ModuleBoundary descriptions
7. **Regular Analysis**: Run weekly to catch architectural drift
8. **Incremental Refactoring**: Use metrics to prioritize cleanup

## Troubleshooting

**No entities detected:**
- Check file extensions are supported (.py, .js, .ts)
- Verify files aren't in ignored directories (node_modules, __pycache__)

**WebSocket won't connect:**
- Check firewall settings
- Verify server is running
- Check browser console for errors

**Analysis is slow:**
- Limit scope to specific directories
- Check for very large files
- Increase debounce time for file watcher

**Incorrect dependencies:**
- Parser may need improvement for specific syntax
- Check for dynamic imports (harder to detect)
- Review AST extraction logic
