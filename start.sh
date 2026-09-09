#!/bin/sh
# OrderYourself Docker entrypoint
set -eu

cd /app
mkdir -p /app/data

export DATABASE_PATH="${DATABASE_PATH:-/app/data/order_yourself.db}"
export PORT="${PORT:-8000}"

echo "Starting OrderYourself on port ${PORT}"
echo "Database: ${DATABASE_PATH}"

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
