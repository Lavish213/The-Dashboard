#!/usr/bin/env bash
# dev/bootstrap.sh — Fresh local DB setup for internal alpha
# Usage: bash scripts/dev/bootstrap.sh [--reset]
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "$0")/../../backend" && pwd)"
PSQL="/opt/homebrew/Cellar/postgresql@16/16.11_1/bin/psql"
CREATEDB="/opt/homebrew/Cellar/postgresql@16/16.11_1/bin/createdb"
DROPDB="/opt/homebrew/Cellar/postgresql@16/16.11_1/bin/dropdb"
DB_NAME="${DB_NAME:-karpathys_dev}"
DB_USER="${DB_USER:-$(whoami)}"
DB_HOST="${DB_HOST:-localhost}"
DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${DB_USER}@${DB_HOST}:5432/${DB_NAME}}"

RESET=0
for arg in "$@"; do
  [[ "$arg" == "--reset" ]] && RESET=1
done

echo "=== Karpathys Dev Bootstrap ==="
echo "DB: ${DB_NAME} on ${DB_HOST} as ${DB_USER}"

# --- Drop/create DB ---
if [[ "$RESET" == "1" ]]; then
  echo "Dropping ${DB_NAME}..."
  "$DROPDB" -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" 2>/dev/null || true
fi

echo "Creating ${DB_NAME} (if not exists)..."
"$CREATEDB" -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" 2>/dev/null || echo "  (already exists)"

# --- Run migrations ---
echo "Running migrations..."
cd "$BACKEND_DIR"
DATABASE_URL="$DATABASE_URL" .venv/bin/alembic upgrade head

# --- Seed admin user ---
echo "Seeding admin user..."
DATABASE_URL="$DATABASE_URL" .venv/bin/python scripts/seed_admin.py

echo ""
echo "=== Bootstrap complete ==="
echo "Login: admin@karpathys.dev / admin1234"
echo "Start server: cd backend && uvicorn api.main:app --reload"
