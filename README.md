# ShandorCode

**Code analysis, architecture visualization, and complexity metrics.**

Part of the [GozerAI](https://gozerai.com) ecosystem.

## Overview

ShandorCode analyzes codebases to produce dependency graphs, complexity metrics, and architecture boundary checks. It ships with parsers for Python and JavaScript/TypeScript, a real-time file watcher, and a FastAPI server with WebSocket support for live visualization. Pro tier adds AI-powered code insights.

## Installation

```bash
git clone https://github.com/GozerAI/shandorcode.git
cd shandorcode
pip install -e ".[dev]"
```

## Quick Start

### Analyze a codebase

```python
from src.core.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer("/path/to/your/repo")
graph = analyzer.analyze()

# Get complexity metrics
metrics = analyzer.get_metrics()
print(f"Total files: {metrics['total_files']}")
print(f"Average complexity: {metrics['avg_complexity']}")
```

### Parse individual files

```python
from src.parsers.python_parser import PythonParser
from src.parsers.javascript_parser import JavaScriptParser

# Parse a Python file
py_parser = PythonParser()
py_result = py_parser.parse("/path/to/module.py")

# Parse a JavaScript/TypeScript file
js_parser = JavaScriptParser()
js_result = js_parser.parse("/path/to/component.tsx")
```

### Check architecture boundaries

```python
violations = analyzer.check_boundaries([
    {"name": "core", "path": "src/core", "allowed_deps": []},
    {"name": "api", "path": "src/api", "allowed_deps": ["core"]},
    {"name": "parsers", "path": "src/parsers", "allowed_deps": ["core"]},
])
```

### Real-time monitoring

```python
from src.core.watcher import FileWatcher

def on_change(changes):
    print(f"Files changed: {changes}")

watcher = FileWatcher("/path/to/repo", on_change)
watcher.start()
```

### Start the API server

```bash
python -m src.api.server --path /path/to/your/repo
# Server runs at http://localhost:8765
```

## Feature Tiers

| Feature | Community | Pro | Enterprise |
|---|:---:|:---:|:---:|
| Code analysis (complexity, LOC, maintainability) | x | x | x |
| Python parser | x | x | x |
| JavaScript/TypeScript parser | x | x | x |
| Dependency graph generation | x | x | x |
| File watcher (real-time updates) | x | x | x |
| Lightning analyzer (fast mode) | x | x | x |
| Architecture boundary checking | | x | x |
| AI-powered semantic search | | x | x |
| Code smell detection | | x | x |
| Refactoring suggestions | | x | x |
| Complexity explanations | | x | x |
| Auto-generated documentation | | x | x |
| Similar code detection | | x | x |
| Advanced visualization | | | x |

### Gated Features

Pro and Enterprise features require a valid entitlement via the GozerAI platform. Visit [gozerai.com/pricing](https://gozerai.com/pricing) to upgrade.

## API Endpoints

### Community (shandorcode:basic)

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/api/analyze` | Analyze a repository |
| GET | `/api/current` | Current analysis results |
| GET | `/api/history` | Analysis history |
| GET | `/api/metrics` | Complexity metrics |
| GET | `/api/metrics/detailed` | Detailed per-file metrics |
| GET | `/api/graph` | Dependency graph data |
| WS | `/ws` | WebSocket for live updates |

### Pro (shandorcode:full)

| Method | Path | Description |
|---|---|---|
| POST | `/api/check-boundaries` | Architecture boundary check |
| POST | `/api/ai/search` | Semantic code search |
| GET | `/api/ai/code-smells` | Detect code smells |
| GET | `/api/ai/refactor-suggestions/{id}` | Refactoring suggestions |
| GET | `/api/ai/complexity-explained/{id}` | Complexity explanation |
| GET | `/api/ai/generate-docs/{id}` | Auto-generate documentation |
| GET | `/api/ai/similar-code/{id}` | Find similar code patterns |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ZUULTIMATE_BASE_URL` | `http://localhost:8000` | Auth service URL |

## Requirements

- Python >= 3.10
- FastAPI + httpx for the API server

## License

Dual-licensed:

- **AGPL-3.0** for open source use (see [LICENSE.txt](LICENSE.txt))
- **Commercial** for proprietary integration (see [LICENSE-COMMERCIAL.txt](LICENSE-COMMERCIAL.txt))

Contact chris@gozerai.com for commercial licensing.
