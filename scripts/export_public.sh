#!/usr/bin/env bash
# export_public.sh — Creates a clean public export of ShandorCode for GozerAI/shandorcode.
# Usage: bash scripts/export_public.sh [target_dir]
#
# Strips proprietary Pro/Enterprise modules and internal infrastructure,
# leaving only community-tier code + the license gate (so users see the upgrade path).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-${REPO_ROOT}/../shandorcode-public-export}"

echo "=== ShandorCode Public Export ==="
echo "Source: ${REPO_ROOT}"
echo "Target: ${TARGET}"

# Clean target
rm -rf "${TARGET}"
mkdir -p "${TARGET}"

# Use git archive to get a clean copy (respects .gitignore, excludes .git)
cd "${REPO_ROOT}"
git archive HEAD | tar -x -C "${TARGET}"

# ===== STRIP PRO MODULES =====
rm -rf "${TARGET}/src/analyzers/"

# ===== STRIP ENTERPRISE MODULES =====
rm -rf "${TARGET}/src/visualization/"

# ===== STRIP INTERNAL DOCS =====
rm -rf "${TARGET}/deployment/"
rm -f "${TARGET}/COMPLETE_SETUP_SUMMARY.md"
rm -f "${TARGET}/DEPLOYMENT_STATUS.md"
rm -f "${TARGET}/PERFORMANCE_UPGRADE.md"
rm -f "${TARGET}/PROJECT_STATUS.md"
rm -f "${TARGET}/PROJECT_SUMMARY.md"
rm -f "${TARGET}/QUICK_REFERENCE.md"
rm -f "${TARGET}/README_GITHUB.md"
rm -f "${TARGET}/RENAME_SUMMARY.md"
rm -f "${TARGET}/reorganize.ps1"
rm -f "${TARGET}/start.bat"
rm -f "${TARGET}/start.sh"
rm -rf "${TARGET}/examples/"
rm -rf "${TARGET}/htmlcov/"

# ===== CREATE STUB __init__.py FOR STRIPPED PACKAGES =====

write_stub() {
    cat > "$1" << 'PYEOF'
"""This module requires a commercial license.

Visit https://gozerai.com/pricing for Pro and Enterprise tier details.
Set VINZY_LICENSE_KEY to unlock licensed features.
"""

raise ImportError(
    f"{__name__} requires a commercial license. "
    "Visit https://gozerai.com/pricing for details."
)
PYEOF
}

# Pro stub (analyzers package)
mkdir -p "${TARGET}/src/analyzers"
write_stub "${TARGET}/src/analyzers/__init__.py"

# Enterprise stub (visualization package)
mkdir -p "${TARGET}/src/visualization"
write_stub "${TARGET}/src/visualization/__init__.py"

# ===== UPDATE pyproject.toml — fix email =====
sed -i 's|chris@gozerai.com|chris@gozerai.com|g' "${TARGET}/pyproject.toml"

# ===== UPDATE README — clean for public =====
cat > "${TARGET}/README.md" << 'MDEOF'
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
MDEOF

# ===== UPDATE LICENSING.md =====
cat > "${TARGET}/LICENSING.md" << 'MDEOF'
# Commercial Licensing — ShandorCode

This project is dual-licensed:

- **AGPL-3.0** — Free for open-source use with copyleft obligations
- **Commercial License** — Proprietary use without AGPL requirements

## Tiers

| | Community (Free) | Pro | Enterprise |
|--|:---:|:---:|:---:|
| Base functionality | Yes | Yes | Yes |
| Advanced analysis | — | Yes | Yes |
| Enterprise visualization | — | — | Yes |

Part of the **GozerAI ecosystem**. See pricing at **https://gozerai.com/pricing**.

```bash
export VINZY_LICENSE_KEY="your-key-here"
```
MDEOF

# ===== FIX remaining gozerai references =====
find "${TARGET}" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.py" -o -name "*.toml" \) -exec sed -i 's|gozerai\.com|gozerai.com|g' {} +
find "${TARGET}" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.py" -o -name "*.toml" \) -exec sed -i 's|GozerAI@|chris@gozerai.com|g' {} +

echo ""
echo "=== Export complete: ${TARGET} ==="
echo ""
echo "Community-tier modules included:"
echo "  __init__.py, api/, core/, licensing.py, parsers/, utils/"
echo ""
echo "Stripped (Pro/Enterprise — replaced with stubs):"
echo "  analyzers/ (Pro), visualization/ (Enterprise)"
echo "  Internal deployment docs, status docs removed"
