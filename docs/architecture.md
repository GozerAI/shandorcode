# ShandorCode Architecture

## Overview

ShandorCode is a real-time code visualization and analysis tool built with a modular, production-ready architecture. It provides live insights into code structure, dependencies, and complexity across multiple programming languages.

## Design Philosophy

1. **Modularity**: Clean separation between parsing, analysis, and visualization
2. **Extensibility**: Plugin-based parser system for adding new languages
3. **Real-time**: File watching and WebSocket updates for live feedback
4. **Security**: Zero-trust architecture with input validation
5. **Performance**: Incremental analysis and efficient graph structures

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Web Browser (Client)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │         D3.js Interactive Visualization          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │ WebSocket (real-time)
                      │ HTTP (REST API)
┌─────────────────────▼───────────────────────────────────┐
│              FastAPI Server (src/api/)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │    WebSocket Handler    │    REST Endpoints     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│           Code Analyzer (src/core/analyzer.py)          │
│  ┌──────────────────────────────────────────────────┐  │
│  │  • File discovery                                │  │
│  │  • Parser orchestration                          │  │
│  │  • Graph building                                │  │
│  │  • Metrics calculation                           │  │
│  │  • Boundary violation detection                  │  │
│  └──────────────────────────────────────────────────┘  │
└───────────┬──────────────────────────┬──────────────────┘
            │                          │
┌───────────▼──────────┐  ┌───────────▼──────────────────┐
│   Language Parsers   │  │   File Watcher               │
│   (src/parsers/)     │  │   (src/core/watcher.py)      │
│  ┌────────────────┐  │  │  ┌────────────────────────┐  │
│  │ Python Parser  │  │  │  │  Watchdog Integration  │  │
│  │ JS/TS Parser   │  │  │  │  Change Debouncing     │  │
│  │ (Extensible)   │  │  │  │  Event Filtering       │  │
│  └────────────────┘  │  │  └────────────────────────┘  │
└──────────────────────┘  └─────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────┐
│              Tree-sitter (AST Parsing)                   │
│  Multi-language abstract syntax tree parsing             │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Data Models (src/core/models.py)

Pydantic-based type-safe models for:
- **CodeEntity**: Represents files, classes, functions, methods
- **Dependency**: Relationships between entities (imports, calls, inheritance)
- **ShandorCode**: Complete graph with entities and dependencies
- **ComplexityMetrics**: Cyclomatic complexity, LOC, maintainability
- **ModuleBoundary**: Architecture rules and constraints
- **BoundaryViolation**: Detected violations of architectural rules

### 2. Language Parsers (src/parsers/)

Each parser uses Tree-sitter for robust AST analysis:

**PythonParser**:
- Extracts classes, functions, methods, imports
- Calculates cyclomatic complexity
- Detects inheritance and call dependencies
- Extracts docstrings

**JavaScriptParser / TypeScriptParser**:
- Handles modern JS/TS syntax
- Supports arrow functions, classes, modules
- ES6+ feature support

**Extensible Design**:
- Implement parser interface
- Register in analyzer
- Automatic language detection

### 3. Code Analyzer (src/core/analyzer.py)

Main orchestration engine:

```python
analyzer = CodeAnalyzer("/path/to/repo")
graph = analyzer.analyze()  # Full analysis
metrics = analyzer.get_metrics()  # Summary stats
violations = analyzer.check_boundaries(boundaries)  # Architecture validation
```

**Responsibilities**:
- File discovery with smart filtering
- Language detection
- Parser routing
- Graph construction
- Metrics aggregation
- Boundary checking

### 4. File Watcher (src/core/watcher.py)

Real-time monitoring using Watchdog:

**Features**:
- File system event monitoring
- Change debouncing (configurable)
- Smart filtering (ignore node_modules, etc.)
- Callback-based architecture

**Usage**:
```python
def on_change(files):
    # Re-analyze changed files
    pass

watcher = FileWatcher("/path", on_change, debounce_seconds=1.0)
watcher.start()
```

### 5. API Server (src/api/server.py)

FastAPI-based server with:

**REST Endpoints**:
- `POST /api/analyze` - Trigger analysis
- `GET /api/metrics` - Get metrics
- `GET /api/graph` - Get full graph
- `POST /api/check-boundaries` - Validate architecture

**WebSocket**:
- `/ws` - Real-time graph updates
- Automatic reconnection
- Heartbeat/ping-pong

### 6. Visualization (Embedded in server.py)

D3.js force-directed graph:

**Features**:
- Interactive node dragging
- Color-coded entity types
- Dependency relationship visualization
- Click for entity details
- Real-time updates via WebSocket

## Data Flow

### Initial Analysis

```
1. User starts server with repository path
2. CodeAnalyzer discovers all code files
3. For each file:
   a. Detect language
   b. Route to appropriate parser
   c. Extract entities and dependencies
4. Build ShandorCode from results
5. Calculate aggregate metrics
6. Send graph to connected WebSocket clients
7. Start FileWatcher for live updates
```

### Live Updates

```
1. User modifies code file
2. FileWatcher detects change
3. Debounce period elapses (1 second)
4. Callback triggers re-analysis
5. Updated graph built
6. Broadcast to all WebSocket clients
7. UI updates visualization
```

### Boundary Checking

```
1. Define ModuleBoundary rules
2. Analyzer checks each dependency
3. For each import dependency:
   a. Determine source module
   b. Determine target module
   c. Check if dependency is allowed
   d. Create BoundaryViolation if not
4. Return list of violations
```

## Extensibility Points

### Adding a New Language

1. Create parser class in `src/parsers/`
2. Inherit from base patterns
3. Implement `parse_file()` method
4. Register in `CodeAnalyzer.parsers`
5. Add language to `LANGUAGE_MAP`

### Custom Analyzers

Extend `CodeAnalyzer` to add custom analysis:

```python
class CustomAnalyzer(CodeAnalyzer):
    def detect_patterns(self):
        # Custom pattern detection
        pass
```

### Additional Metrics

Add to `ComplexityMetrics` model and update parsers:

```python
class ComplexityMetrics(BaseModel):
    # ... existing fields ...
    halstead_volume: Optional[float] = None
```

## Security Considerations

1. **Input Validation**: All file paths validated
2. **Path Traversal Prevention**: Resolved paths only
3. **Resource Limits**: File size and count limits
4. **No Code Execution**: Pure static analysis
5. **Sanitized Output**: No sensitive data exposure

## Performance Optimization

1. **Incremental Analysis**: Only re-parse changed files
2. **Debouncing**: Batch rapid changes
3. **Lazy Loading**: Parse on demand
4. **Efficient Graph Structure**: NetworkX optimization
5. **Caching**: Parser results cache (future)

## Error Handling

Three-tier error strategy:

1. **Parse Errors**: Skip problematic files, log, continue
2. **Analysis Errors**: Graceful degradation
3. **System Errors**: Proper exceptions, user feedback

## Deployment Architecture

```
Development:
- Local FastAPI server
- File watcher enabled
- Debug logging

Production:
- Uvicorn workers
- Reverse proxy (nginx)
- File watcher optional
- Structured logging
- Metrics collection
```

## Future Enhancements

1. **Graph Database**: Neo4j integration for complex queries
2. **Historical Analysis**: Track architecture evolution
3. **CI/CD Integration**: Automated boundary checks
4. **Plugin System**: Third-party analyzers
5. **Cloud Storage**: Remote repository analysis
6. **AI Analysis**: LLM-based code understanding
7. **Performance Profiling**: Runtime analysis
8. **Security Scanning**: Vulnerability detection

## Integration with GozerAI Ecosystem

ShandorCode aligns with the modular GozerAI architecture:

- **Plugin-SDK**: Provides parser interface contracts
- **Vinzy-Engine**: Manages analysis licensing
- **Zuultimate**: Handles auth for multi-user deployments
- **n8n Workflows**: Triggers analysis on commit hooks
- **Notion Databases**: Stores architecture decisions

This positions ShandorCode as both a standalone tool and a GozerAI ecosystem component.
