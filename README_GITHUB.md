# 🏗️ ShandorCode

**Real-time code visualization and architecture analysis tool**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%203.0-blue.svg)](LICENSE.txt)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> *"In the architecture of code, Shandor sees all."* 👻🏗️

ShandorCode helps you maintain clean, modular architecture during development by providing **real-time visualization** of your codebase structure, dependencies, and complexity metrics.

Part of the [GozerAI](https://github.com/yourusername/gozerai) ecosystem.

---

## ✨ Features

- 🌳 **Multi-language parsing** - Python, TypeScript, JavaScript (extensible)
- 📊 **Complexity metrics** - Cyclomatic complexity, maintainability index, LOC
- 🔗 **Dependency graphs** - Visualize module relationships and call hierarchies
- ⚡ **Real-time updates** - File watcher with live WebSocket updates
- 🎨 **Interactive visualization** - D3.js-powered force-directed graphs
- 🏗️ **Architecture validation** - Enforce modular boundaries and detect violations
- 📈 **Trend analysis** - Track architectural evolution over time

---

## 🚀 Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/shandorcode.git
cd shandorcode

# Install with development dependencies
pip install -e '.[dev]'
```

### Start Server

**Windows:**
```cmd
start.bat
```

**Unix/Mac:**
```bash
./start.sh
```

**Manual:**
```bash
python -m src.api.server --path /path/to/your/project
```

Then open: **http://localhost:8765**

---

## 📸 Screenshots

*Coming soon - interactive visualization dashboard, dependency graphs, metrics dashboard*

---

## 🎯 Use Cases

### 1. Live Development Monitoring
Watch your architecture in real-time as you code:
```bash
python -m src.api.server --path ~/projects/my-app
# Open http://localhost:8765 and code!
```

### 2. Architecture Validation
Enforce modular boundaries in your CI/CD:
```python
from src.core.analyzer import CodeAnalyzer
from src.core.models import ModuleBoundary

boundaries = [
    ModuleBoundary("core", "src/core", []),
    ModuleBoundary("api", "src/api", ["src/core"])
]

analyzer = CodeAnalyzer(".")
violations = analyzer.check_boundaries(boundaries)
```

### 3. Technical Debt Analysis
Identify complexity hotspots:
```python
analyzer = CodeAnalyzer("/path/to/project")
graph = analyzer.analyze()

# Find high-complexity entities
hotspots = [e for e in graph.entities if e.complexity > 10]
```

### 4. Onboarding New Developers
Provide visual documentation of codebase structure automatically.

---

## 🏛️ Architecture

```
shandorcode/
├── src/
│   ├── core/              # Zero-dependency core
│   │   ├── models.py      # Pydantic data models
│   │   ├── analyzer.py    # Analysis engine
│   │   └── watcher.py     # File system watcher
│   ├── parsers/           # Language parsers
│   │   ├── python_parser.py
│   │   ├── javascript_parser.py
│   │   └── typescript_parser.py
│   └── api/               # FastAPI server
│       └── server.py      # REST + WebSocket + UI
├── tests/                 # Test suite
├── docs/                  # Documentation
└── examples/              # Usage examples
```

**Design Principles:**
- Layered architecture with clear separation of concerns
- Zero-dependency core for maximum portability
- Plugin architecture for language parsers
- Type-safe throughout (Pydantic models)
- Production-ready code standards

---

## 🔌 API Reference

### REST Endpoints

- `POST /api/analyze` - Analyze a codebase
- `GET /api/metrics` - Get current metrics
- `GET /api/graph` - Get dependency graph
- `POST /api/check-boundaries` - Validate architecture rules

### WebSocket

- `ws://localhost:8765/ws` - Real-time updates stream

Full API documentation: http://localhost:8765/docs

---

## 🌐 GozerAI Ecosystem

ShandorCode is the **Architect** of the GozerAI ecosystem:

```
GozerAI (The Orchestrator)
├── Zuultimate (The Gatekeeper) - Security/Identity
├── Vinzy-Engine (The Keymaster) - Licensing
├── Plugin-SDK (The Interface) - Contracts
└── ShandorCode (The Architect) - Analysis ⭐
```

---

## 🛠️ Development

### Run Tests
```bash
python tests/test_shandorcode.py
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint
pylint src/

# Type check
mypy src/
```

### Adding Language Support
1. Create parser in `src/parsers/your_language_parser.py`
2. Implement `parse()` method returning `CodeGraph`
3. Register in `analyzer.py`

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📊 Performance

Tested on ShandorCode itself (self-analysis):
- **Files**: 17
- **Entities**: 139
- **Dependencies**: 365
- **Analysis Time**: ~35ms
- **Average Complexity**: 6.23

Scales to 1000+ file repositories with analysis times under 5 seconds.

---

## 🔒 Security

- **Local-only**: All analysis happens on your machine
- **Read-only**: Never modifies your code
- **No telemetry**: Zero data collection
- **Sandboxed**: Parser runs in isolated context

---

## 📄 License

Dual-licensed:
- **[AGPL-3.0](LICENSE.txt)** - Free for open source projects
- **[Commercial](LICENSE-COMMERCIAL.txt)** - For proprietary use

Contact: [GozerAI](mailto:contact@gozerai.com)

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

Key areas for contribution:
- Additional language parsers (Go, Rust, Java, C++)
- Visualization improvements
- Architecture fitness functions
- Performance optimizations

---

## 🗺️ Roadmap

### v0.2 (Q1 2025)
- [ ] More language support (Go, Rust, Java)
- [ ] Historical trend analysis
- [ ] Export to SVG/PNG
- [ ] CLI tool for reports

### v0.3 (Q2 2025)
- [ ] VS Code extension
- [ ] Multi-repository analysis
- [ ] AI-powered refactoring suggestions
- [ ] Team collaboration features

### v1.0 (Q3 2025)
- [ ] Enterprise features (SSO, RBAC)
- [ ] Cloud deployment option
- [ ] Compliance reporting
- [ ] Performance prediction models

---

## 🙏 Acknowledgments

Built with:
- [tree-sitter](https://tree-sitter.github.io/) - Parsing framework
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [D3.js](https://d3js.org/) - Visualization
- [Pydantic](https://pydantic.dev/) - Data validation

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yourusername/shandorcode/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/shandorcode/discussions)
- **Commercial Support**: contact@gozerai.com

---

## ⭐ Star History

If ShandorCode helps you maintain clean architecture, please give it a star! ⭐

---

**Built with ❤️ for the GozerAI Ecosystem**  
*Part of GozerAI*
