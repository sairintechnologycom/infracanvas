#!/usr/bin/env bash
# smoke_release.sh — run the same `alembic upgrade head` command that Fly's
# release_command will run, against a real Neon (dev) connection. Used in CI
# to catch migration breakage before it lands in main (VALIDATION.md
# § Validation Dimension 8).
#
# Required env:
#   DATABASE_URL_MIGRATOR  Neon owner connection string (non-pooled)
# Optional:
#   DATABASE_URL           pooled connection (defaults to DATABASE_URL_MIGRATOR)
set -euo pipefail

: "${DATABASE_URL_MIGRATOR:?DATABASE_URL_MIGRATOR must be set}"
: "${DATABASE_URL:=$DATABASE_URL_MIGRATOR}"
export DATABASE_URL DATABASE_URL_MIGRATOR

cd "$(dirname "$0")/.."
alembic -c alembic.ini upgrade head
echo "OK: alembic upgrade head green against \$DATABASE_URL_MIGRATOR"
