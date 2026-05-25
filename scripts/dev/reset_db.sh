#!/usr/bin/env bash
# dev/reset_db.sh — Nuke and recreate dev DB, re-run migrations, re-seed
# Usage: bash scripts/dev/reset_db.sh
set -euo pipefail

exec bash "$(dirname "$0")/bootstrap.sh" --reset "$@"
