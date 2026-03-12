# ShandorCode

**AI code analysis and optimization toolkit** — Part of the [GozerAI](https://gozerai.com) ecosystem.

## Overview

ShandorCode is a production-ready tool for visualizing code structure, dependencies, and complexity metrics across multiple programming languages. It provides real-time updates during development sessions, helping you maintain clean architecture.

## Features (Community Tier)

- **Multi-language parsing** — Python, TypeScript, JavaScript (extensible)
- **Complexity metrics** — Cyclomatic complexity, maintainability index, lines of code
- **Dependency graphs** — Module relationships, import hierarchies, call graphs
- **Real-time updates** — File watcher with live WebSocket updates
- **Architecture validation** — Detect violations of modular boundaries
- **FastAPI server** — WebSocket support for live analysis

### Pro Features (requires license)

- Advanced AI-powered code analysis and insights
- Pattern detection and recommendations

### Enterprise Features (requires license)

- Interactive D3.js visualization with multiple view modes
- Enhanced UI dashboards

Visit [gozerai.com/pricing](https://gozerai.com/pricing) for Pro and Enterprise tier details.

## Installation

```bash
pip install -e '.[dev]'
```

## Quick Start

```bash
# Start ShandorCode server
python -m src.api.server --path /path/to/your/repo

# Open browser to http://localhost:8765
```

## Usage

```python
from src.core.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer("/path/to/repo")
graph = analyzer.analyze()

# Get dependency metrics
metrics = analyzer.get_metrics()

# Check for architecture violations
violations = analyzer.check_boundaries([
    {"name": "core", "path": "src/core", "allowed_deps": []},
    {"name": "api", "path": "src/api", "allowed_deps": ["core"]},
])
```

## Running Tests

```bash
pytest tests/ -v
```

## Requirements

- Python >= 3.9
- See pyproject.toml for dependencies

## License

This project is dual-licensed:

- **AGPL-3.0** — For open-source use (see [LICENSE](LICENSE))
- **Commercial** — For proprietary integration

Contact chris@gozerai.com for commercial licensing.

## Security

For security issues, please email security@gozerai.com rather than using the issue tracker.

## Links

- [GozerAI Ecosystem](https://gozerai.com)
- [Pricing](https://gozerai.com/pricing)
