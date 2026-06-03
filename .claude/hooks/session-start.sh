#!/bin/bash
set -euo pipefail

# Always configure git identity for this project
git config user.name "sam-razavi"
git config user.email "h24sasah@du.se"

# Only run the install steps in Claude Code remote (web) sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "==> Installing backend dependencies..."
cd "$CLAUDE_PROJECT_DIR/backend"
if command -v uv &>/dev/null; then
  uv pip install -e ".[dev]" --system --quiet
else
  pip install -e ".[dev]" --quiet
fi

echo "==> Installing frontend dependencies..."
cd "$CLAUDE_PROJECT_DIR/frontend"
npm install --silent

echo "==> Session start complete."
