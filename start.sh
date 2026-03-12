#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# CodeGraph startup script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║                                       ║"
echo "║       CodeGraph Visualizer            ║"
echo "║    Real-time Code Analysis Tool       ║"
echo "║                                       ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Parse arguments
REPO_PATH=${1:-.}
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

echo -e "${GREEN}Starting CodeGraph...${NC}"
echo -e "  Repository: ${YELLOW}$REPO_PATH${NC}"
echo -e "  Server: ${YELLOW}http://$HOST:$PORT${NC}"
echo ""

# Check if dependencies are installed
echo -e "${BLUE}Checking dependencies...${NC}"
python3 -c "import tree_sitter, fastapi, watchdog" 2>/dev/null || {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install --break-system-packages -q \
        tree-sitter tree-sitter-python tree-sitter-javascript tree-sitter-typescript \
        watchdog fastapi uvicorn websockets networkx pydantic radon pygments
    echo -e "${GREEN}✓ Dependencies installed${NC}"
}

echo -e "${GREEN}✓ Dependencies ready${NC}"
echo ""

# Run the server
echo -e "${BLUE}Launching server...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

python3 -m src.api.server \
    --host "$HOST" \
    --port "$PORT" \
    --path "$REPO_PATH"
