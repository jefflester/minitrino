#!/usr/bin/env bash

# Validate that pytest can collect all tests without errors
# This ensures test files are syntactically correct and properly structured

set -euo pipefail

# Activate virtual environment if it exists
if [ -d "venv/bin" ]; then
    PYTHON="venv/bin/python"
    PYTEST="venv/bin/pytest"
elif command -v python3 &> /dev/null; then
    PYTHON="python3"
    PYTEST="pytest"
else
    PYTHON="python"
    PYTEST="pytest"
fi

# Check if pytest is installed
if ! command -v $PYTEST &> /dev/null && ! $PYTHON -m pytest --version &> /dev/null 2>&1; then
    echo "⚠️  pytest not installed, skipping test collection validation"
    exit 0
fi

echo "🧪 Validating pytest can collect all tests..."

# Try to collect tests without running them
if $PYTHON -m pytest src/tests/ --collect-only -q > /dev/null 2>&1; then
    echo "✅ All tests collected successfully"
    exit 0
else
    echo "❌ Failed to collect tests - check for syntax errors or import issues"
    echo ""
    echo "Running pytest --collect-only to show errors:"
    $PYTHON -m pytest src/tests/ --collect-only -q
    exit 1
fi
