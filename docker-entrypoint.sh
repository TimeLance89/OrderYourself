#!/bin/sh
# Interner Container-Entrypoint für den buildx-freien UGREEN-Stack.
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

# Der Docker-Volume-Mount selbst darf niemals gelöscht werden.
# Deshalb liegt die eigentliche virtuelle Umgebung in einem Unterordner.
VOLUME_ROOT="/opt/orderyourself-venv"
VENV_DIR="$VOLUME_ROOT/venv"
REQ_FILE="/app/requirements.txt"
MARKER="$VENV_DIR/.requirements.sha256"

mkdir -p "$VOLUME_ROOT"
REQ_HASH=$(sha256sum "$REQ_FILE" | awk '{print $1}')
CURRENT_HASH=""
[ -f "$MARKER" ] && CURRENT_HASH=$(cat "$MARKER" || true)

if [ ! -x "$VENV_DIR/bin/python" ] || [ "$CURRENT_HASH" != "$REQ_HASH" ]; then
    echo "Installing/updating OrderYourself Python dependencies ..."
    rm -rf "$VENV_DIR"
    python -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install --no-cache-dir --upgrade pip
    "$VENV_DIR/bin/python" -m pip install --no-cache-dir -r "$REQ_FILE"
    printf '%s' "$REQ_HASH" > "$MARKER"
else
    echo "Python dependencies are already up to date."
fi

"$VENV_DIR/bin/python" - <<'PY'
import fastapi, sqlmodel, uvicorn, httpx
print("Dependency check: OK")
PY

echo "Starting OrderYourself on port ${PORT}"
echo "Database: ${DATABASE_PATH}"

exec "$VENV_DIR/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$PORT"
