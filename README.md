# ShandorCode

[![GozerAI](https://img.shields.io/badge/GozerAI-ecosystem-5eead4?style=flat-square&labelColor=0b0e14)](https://github.com/GozerAI) [![License](https://img.shields.io/badge/license-AGPL--3.0-3b82f6?style=flat-square)](LICENSE) [![Python](https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org) [![Pro & Enterprise](https://img.shields.io/badge/Pro%20%26%20Enterprise-gozerai.com-fbbf24?style=flat-square)](https://gozerai.com/pricing)

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
from src.visualization.core.analyzer import CodeAnalyzer
from src.visualization.core.models import ModuleBoundary

analyzer = CodeAnalyzer("/path/to/repo")
graph = analyzer.analyze()

# Get dependency metrics
metrics = analyzer.get_metrics()

# Check for architecture violations
violations = analyzer.check_boundaries([
    ModuleBoundary(name="core", path="src/visualization/core", allowed_dependencies=[]),
    ModuleBoundary(name="api", path="src/api", allowed_dependencies=["core"]),
])
```

## Running Tests

```bash
pytest tests/ -v
```

## Requirements

- Python >= 3.12
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
