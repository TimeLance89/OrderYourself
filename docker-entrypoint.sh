#!/bin/sh
# Interner Container-Entrypoint für OrderYourself.
set -eu

cd /app
mkdir -p /app/data

export DATABASE_PATH="${DATABASE_PATH:-/app/data/order_yourself.db}"
export PORT="${PORT:-8000}"

python - <<'PY'
import sys
if sys.version_info[:2] != (3, 12):
    raise SystemExit(
        f"OrderYourself erwartet Python 3.12, gefunden: {sys.version.split()[0]}"
    )
print(f"Python runtime: {sys.version.split()[0]}")
PY

echo "Starting OrderYourself on port ${PORT}"
echo "Database: ${DATABASE_PATH}"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
