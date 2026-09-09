#!/bin/sh
# OrderYourself NAS-/Host-Starter für UGREEN ohne buildx.
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

echo "[1/4] Alte OrderYourself-Container stoppen ..."
compose down --remove-orphans || true
docker rm -f OrderYourself orderyourself-v2 >/dev/null 2>&1 || true

echo "[2/4] Python-3.12-Basisimage laden ..."
compose pull orderyourself

echo "[3/4] OrderYourself ohne Docker-Build neu erstellen ..."
compose up -d --force-recreate orderyourself

echo "[4/4] Status anzeigen ..."
sleep 3
compose ps

echo
echo "OrderYourself wurde ohne buildx gestartet."
echo "Beim ersten Start werden die Python-Abhängigkeiten im Container installiert."
echo "Logs: docker compose logs -f orderyourself"
