# ShandorCode Quick Reference

## 🚀 Quick Start Commands

```bash
# Start server (analyze current directory)
./start.sh

# Analyze specific project
./start.sh /path/to/your/project

# Custom host/port
HOST=0.0.0.0 PORT=8080 ./start.sh /path/to/project

# Run test
python test_shandorcode.py

# Example analysis
python examples/analyze_gozerai_project.py /path/to/project
```

## 📊 Programmatic API

### Basic Analysis
```python
from src.core.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer("/path/to/repo")
graph = analyzer.analyze()

# Get metrics
metrics = analyzer.get_metrics()
print(f"Files: {metrics['total_files']}")
print(f"Complexity: {metrics['avg_complexity']:.2f}")
```

### Boundary Checking
```python
from src.core.models import ModuleBoundary

boundaries = [
    ModuleBoundary(
        name="core",
        path="/path/to/repo/src/core",
        allowed_dependencies=[]
    ),
    ModuleBoundary(
        name="api",
        path="/path/to/repo/src/api",
        allowed_dependencies=["core"]
    ),
]

violations = analyzer.check_boundaries(boundaries)
for v in violations:
    print(f"⚠️  {v.message}")
```

### Real-time Monitoring
```python
from src.core.watcher import FileWatcher

def on_change(files):
    graph = analyzer.analyze()
    print(f"Updated: {len(files)} files")

watcher = FileWatcher("/path/to/repo", on_change)
watcher.start()
```

## 🌐 Web Interface

Open browser to `http://localhost:8765`

### Controls
- **Drag nodes** - Rearrange graph
- **Click nodes** - View entity details  
- **Reset View** - Restore layout
- **Toggle Dependencies** - Show/hide edges

### Status Indicators
- 🟢 Connected - Live updates active
- 🔴 Disconnected - No real-time updates

## 🔧 REST API Endpoints

```bash
# Trigger analysis
POST /api/analyze
Body: {"path": "/path/to/repo"}

# Get metrics
GET /api/metrics

# Get full graph
GET /api/graph

# Check boundaries
POST /api/check-boundaries
Body: {"boundaries": [...]}
```

## 📡 WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8765/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'update') {
        // Graph updated
    }
};
```

## 📈 Key Metrics

| Metric | What It Measures | Good Range |
|--------|------------------|------------|
| Cyclomatic Complexity | Decision points | < 10 |
| LOC | Lines of code | Varies |
| Avg Complexity | Overall complexity | < 8 |
| Module Coupling | Cross-dependencies | Minimal |
| Violations | Architecture breaks | 0 |

## 🎯 Common Patterns

### GozerAI Module Boundaries
```python
boundaries = [
    ModuleBoundary(name="core", path="src/core", allowed_dependencies=[]),
    ModuleBoundary(name="plugins", path="src/plugins", allowed_dependencies=["core"]),
    ModuleBoundary(name="api", path="src/api", allowed_dependencies=["core", "plugins"]),
]
```

### Pre-commit Hook
```bash
#!/bin/bash
python examples/analyze_gozerai_project.py . || exit 1
```

### CI/CD Check
```yaml
- run: python examples/analyze_gozerai_project.py .
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No entities found | Check file extensions (.py, .js, .ts) |
| WebSocket won't connect | Check firewall, verify server running |
| Analysis slow | Limit scope, increase debounce time |
| Deps not installed | Run: `pip install -e .` |

## 📁 File Locations

```
/src/core/models.py       - Data models
/src/core/analyzer.py     - Main engine
/src/parsers/*.py         - Language parsers
/src/api/server.py        - Web server
/docs/architecture.md     - System design
/docs/usage.md           - Full guide
```

## 🎨 Entity Types (Colors in UI)

- 🔵 **File** (blue) - Source files
- 🟢 **Class** (green) - Classes
- 🟠 **Function** (orange) - Functions
- 🟣 **Method** (purple) - Methods

## 🔗 Dependency Types

- **Import** - Module imports
- **Call** - Function calls
- **Inheritance** - Class inheritance

## ⚡ Performance Tips

1. Analyze specific directories: `./start.sh src/core`
2. Increase debounce: `debounce_seconds=2.0`
3. Limit file count: Focus on key modules
4. Use boundary checks selectively

## 🔐 Security

- Input validation on all paths
- No code execution (static analysis only)
- Sanitized output
- AGPL-3.0 for open source
- Commercial license available

## 📞 Support

- Issues: Use GitHub issues
- Commercial: chris@gozerai.com
- Docs: /docs/architecture.md, /docs/usage.md
