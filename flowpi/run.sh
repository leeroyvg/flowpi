#!/bin/bash

set -euo pipefail

echo "Starting Flow System..."

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_HOST="${FLOWPI_HOST:-0.0.0.0}"
BACKEND_PORT="${FLOWPI_PORT:-5000}"
FRONTEND_PORT="${FLOWPI_FRONTEND_PORT:-8000}"

# ---------------- BACKEND ----------------
echo "Starting backend..."
cd "$BASE_DIR"
waitress-serve --host "$BACKEND_HOST" --port "$BACKEND_PORT" backend.app:app &
BACKEND_PID=$!

# ---------------- FRONTEND ----------------
echo "Starting frontend..."
cd "$BASE_DIR/frontend"
python3 -m http.server "$FRONTEND_PORT" &
FRONTEND_PID=$!

echo "-----------------------------------"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "System running!"
echo "Open: http://<pi-ip>:$FRONTEND_PORT"
echo "-----------------------------------"

# ---------------- CLEAN EXIT ----------------
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT

wait
