#!/usr/bin/env bash

# Run vulture to detect unused code in the minitrino project
# This script is informational only and will not fail the pre-commit hook

set -euo pipefail

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    PYTHON="venv/bin/python"
    VULTURE="venv/bin/vulture"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
    VULTURE="vulture"
else
    PYTHON="python"
    VULTURE="vulture"
fi

# Check if vulture is installed
if ! command -v $VULTURE &> /dev/null && ! $PYTHON -m vulture --version &> /dev/null 2>&1; then
    echo "⚠️  vulture not installed, skipping dead code detection"
    exit 0
fi

echo "🔍 Checking for unused code with vulture..."

# Run vulture on source directories, excluding tests and generated files
$VULTURE src/cli/minitrino/ \
    --exclude src/tests/ \
    --min-confidence 80 \
    --sort-by-size || true

exit 0
