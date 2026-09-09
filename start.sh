#!/bin/sh
# OrderYourself NAS-/Host-Starter
# Stoppt alte Container und erzwingt einen frischen Python-3.12-Build.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if ! command -v docker >/dev/null 2>&1; then
    echo "FEHLER: Docker wurde nicht gefunden."
    exit 1
fi

if docker compose version >/dev/null 2>&1; then
    compose() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
    compose() { docker-compose "$@"; }
else
    echo "FEHLER: Weder 'docker compose' noch 'docker-compose' ist verfügbar."
    exit 1
fi

if [ ! -f .env ] && [ -f .env.example ]; then
    cp .env.example .env
    echo ".env aus .env.example erstellt."
fi

mkdir -p data

echo "[1/5] Alte OrderYourself-Container stoppen ..."
compose down --remove-orphans || true

echo "[2/5] Eventuell vorhandenen v2-Container entfernen ..."
docker rm -f orderyourself-v2 >/dev/null 2>&1 || true

echo "[3/5] Frisches Image ohne Build-Cache erstellen ..."
compose build --no-cache --pull orderyourself

echo "[4/5] Python-Version im neuen Image pruefen ..."
PYTHON_VERSION=$(compose run --rm --no-deps --entrypoint python orderyourself -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [ "$PYTHON_VERSION" != "3.12" ]; then
    echo "FEHLER: Erwartet Python 3.12, gebaut wurde Python $PYTHON_VERSION"
    exit 1
fi
echo "Python $PYTHON_VERSION OK."

echo "[5/5] OrderYourself neu starten ..."
compose up -d --force-recreate orderyourself

echo
compose ps
echo
echo "OrderYourself wurde neu gebaut und gestartet."
echo "Logs: docker compose logs -f orderyourself"
