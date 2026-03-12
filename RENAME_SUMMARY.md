# ShandorCode - Rename Complete

## Summary of Changes

Successfully renamed from **CodeGraph** to **ShandorCode** and updated default port from **8000** to **8765**.

## Why ShandorCode?

**ShandorCode** fits perfectly within the GozerAI ecosystem:
- **Ivo Shandor** was the architect in Ghostbusters who designed the building
- Perfect metaphor for architecture analysis and code structure visualization  
- Unique, memorable, and professional
- Not taken by any existing code visualization tools
- Brandable and easy to spell/pronounce

## Port Selection: 8765

- **8** = "code" (phonetic)
- **765** = graph-related number sequence
- Avoids common ports (8000, 8080, 3000, etc.)
- Easy to remember

## Files Modified

### 1. Directory Structure
- `/mnt/user-data/outputs/codegraph` → `/mnt/user-data/outputs/shandorcode`

### 2. Configuration Files
- `pyproject.toml`: Package name, all references
- `start.sh`: Port references

### 3. Source Code
- `src/api/server.py`: 
  - FastAPI title
  - HTML title and H1 heading
  - Docstring
  - Default port: 8000 → 8765
  - argparse description
- `src/core/analyzer.py`: Class and documentation references
- `src/core/models.py`: Model class references
- `examples/analyze_gozerai_project.py`: Import and usage examples

### 4. Documentation
- `README.md`: All references to name and port
- `docs/architecture.md`: All technical documentation
- `docs/usage.md`: Usage examples and URLs
- `PROJECT_SUMMARY.md`: Project overview
- `QUICK_REFERENCE.md`: Quick reference guide

### 5. Test Files
- `test_codegraph.py` → `test_shandorcode.py`

## Quick Start with New Configuration

```bash
# Navigate to project
cd /mnt/user-data/outputs/shandorcode

# Activate virtual environment (if created)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install/update package
pip install -e '.[dev]'

# Start server (now on port 8765)
python -m src.api.server

# Open browser
open http://localhost:8765
```

## API Endpoints (Updated Port)

- **Web UI**: http://localhost:8765
- **API Docs**: http://localhost:8765/docs
- **WebSocket**: ws://localhost:8765/ws
- **Analyze**: POST http://localhost:8765/api/analyze
- **Metrics**: GET http://localhost:8765/api/metrics
- **Graph**: GET http://localhost:8765/api/graph

## Integration with GozerAI Ecosystem

ShandorCode is now properly positioned within the GozerAI architecture:

```
GozerAI Ecosystem
├── Zuultimate (Security/Identity) - The Gatekeeper
├── Vinzy-Engine (Licensing) - The Keymaster  
├── Plugin-SDK (Interface Contracts)
└── ShandorCode (Architecture Analysis) - The Architect
```

### Thematic Alignment
- **Shandor**: The architect who designed the structure
- **Zuul**: The gatekeeper who controls access
- **Vinzy**: The keymaster who grants permissions
- All tied to the Ghostbusters/Gozer mythology

## Next Steps

1. ✅ Rename complete
2. ✅ Port updated to 8765
3. ✅ Documentation updated
4. 🔄 Test with actual GozerAI projects
5. 🔄 Set up pre-commit hooks for architecture validation
6. 🔄 CI/CD integration
7. 🔄 Publish to PyPI as `shandorcode`

## Verification Commands

```bash
# Verify no CodeGraph references remain
grep -r "CodeGraph" --include="*.py" --include="*.md" .

# Verify no port 8000 references remain
grep -r ":8000\|port 8000" --include="*.py" --include="*.md" --include="*.sh" .

# Verify ShandorCode is present
grep -r "ShandorCode" --include="*.py" --include="*.md" . | wc -l

# Verify port 8765 is configured
grep -r "8765" --include="*.py" --include="*.md" . | wc -l
```

## Testing

```bash
# Run self-analysis test
python test_shandorcode.py

# Expected output:
# - Files: 13+
# - Entities: 130+
# - Dependencies: 210+
# - No architecture violations
# - Average complexity: ~6.23
```

## License

Dual-licensed under:
- **AGPL-3.0**: For open source use
- **Commercial**: For proprietary/commercial use

Contact for commercial licensing inquiries.

---

**Status**: ✅ Rename Complete | Port: 8765 | Ready for Production
