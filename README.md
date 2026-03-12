# ShandorCode

**Real-time code visualization and architecture analysis tool**

ShandorCode is a production-ready tool for visualizing code structure, dependencies, and complexity metrics across multiple programming languages. It provides real-time updates during development sessions, helping you maintain clean architecture and avoid creating "Frankenstein" products.

## Features

- 🌳 **Multi-language parsing**: Python, TypeScript, JavaScript (extensible to more)
- 📊 **Complexity metrics**: Cyclomatic complexity, maintainability index, lines of code
- 🔗 **Dependency graphs**: Module relationships, import hierarchies, call graphs
- ⚡ **Real-time updates**: File watcher with live WebSocket visualization updates
- 🎨 **Interactive visualization**: D3.js-powered graphs with multiple view modes
- 🏗️ **Architecture validation**: Detect violations of modular boundaries
- 📈 **Trend analysis**: Track how architecture evolves over time

## Installation

```bash
# Clone repository
git clone <repository-url>
cd shandorcode

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e '.[dev]'
```

## Quick Start

```bash
# Start ShandorCode server
python -m src.api.server --path /path/to/your/repo

# Open browser to http://localhost:8765
# Watch your code structure update in real-time!
```

## Usage

### Analyze a Repository

```python
from src.core.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer("/path/to/repo")
graph = analyzer.analyze()

# Get dependency metrics
metrics = analyzer.get_metrics()
print(f"Total files: {metrics['total_files']}")
print(f"Average complexity: {metrics['avg_complexity']}")

# Check for architecture violations
violations = analyzer.check_boundaries([
    {"name": "core", "path": "src/core", "allowed_deps": []},
    {"name": "api", "path": "src/api", "allowed_deps": ["core"]},
])
```

### Real-time Monitoring

```python
from src.core.watcher import FileWatcher

def on_change(changes):
    print(f"Files changed: {changes}")
    # Reanalyze and update visualization

watcher = FileWatcher("/path/to/repo", on_change)
watcher.start()
```

## Architecture

ShandorCode follows a modular architecture:

- **Core**: Analysis engine and graph building
- **Parsers**: Language-specific AST parsing (Tree-sitter based)
- **Analyzers**: Metrics calculation and pattern detection
- **Visualization**: Web-based interactive displays
- **API**: FastAPI server with WebSocket support
- **Utils**: Shared utilities and helpers

## License

This project is dual-licensed:

- **AGPL-3.0**: For open source use (see LICENSE.txt)
- **Commercial**: For proprietary integration (see LICENSE-COMMERCIAL.txt)

Contact chris@gozerai.com for commercial licensing.

## Contributing

See CONTRIBUTING.md for development guidelines.

## Security

For security issues, please email security@gozerai.com rather than using the issue tracker.

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Parser Development](docs/parsers.md)
- [Security Model](docs/security.md)
