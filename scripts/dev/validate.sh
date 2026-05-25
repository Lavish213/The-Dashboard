#!/usr/bin/env bash
# dev/validate.sh — Backend validation gate (ruff + pytest)
# Usage: bash scripts/dev/validate.sh
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/../../backend" && pwd)"
cd "$BACKEND_DIR"

echo "=== Ruff lint ==="
.venv/bin/ruff check .

echo ""
echo "=== Ruff format check ==="
.venv/bin/ruff format --check .

echo ""
echo "=== Pytest ==="
.venv/bin/pytest tests/ -q --tb=short

echo ""
echo "=== All validations passed ==="
