#!/bin/bash

echo "Starting Flow System..."

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------- BACKEND ----------------
echo "Starting backend..."
cd "$BASE_DIR"
python3 -m backend.app &
BACKEND_PID=$!

# ---------------- FRONTEND ----------------
echo "Starting frontend..."
cd "$BASE_DIR/frontend"
python3 -m http.server 8000 &
FRONTEND_PID=$!

echo "-----------------------------------"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "System running!"
echo "Open: http://<pi-ip>:8000"
echo "-----------------------------------"

# ---------------- CLEAN EXIT ----------------
trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID; exit" SIGINT

wait
