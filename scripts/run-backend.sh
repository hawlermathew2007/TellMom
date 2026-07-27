#!/usr/bin/env bash

set -euo pipefail

SESSION="dev"

# Install dependencies
uv sync

# Start containers
docker compose up -d

echo "Waiting for PostgreSQL..."
POSTGRES_ID="$(docker compose ps -q postgres)"

until [ "$(docker inspect -f '{{.State.Health.Status}}' "$POSTGRES_ID")" = "healthy" ]; do
    sleep 1
done

echo "Database is ready."

sh ./scripts/create-db.sh

# Create tmux session if needed
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux new-session -d -s "$SESSION" -n temp
fi

# Ensure temp exists at window 0
if ! tmux list-windows -t "$SESSION" -F '#I' | grep -qx '^0$'; then
    tmux new-window -d -t "$SESSION:0" -n temp
fi

# Remove every window except temp (0)
tmux list-windows -t "$SESSION" -F '#I' |
while read -r idx; do
    if [ "$idx" != "0" ]; then
        tmux kill-window -t "$SESSION:$idx"
    fi
done

# Create fresh windows
tmux new-window -t "$SESSION:1" -n services
tmux new-window -t "$SESSION:2" -n backend-tui
tmux new-window -t "$SESSION:3" -n adapter-tui

# Build a clean 2x2 grid in services
tmux split-window -h -t "$SESSION:1"
tmux split-window -v -t "$SESSION:1.0"
tmux split-window -v -t "$SESSION:1.1"
tmux select-layout -t "$SESSION:1" tiled

# Services
tmux send-keys -t "$SESSION:1.0" "uv run python -m proxy.main" C-m
tmux send-keys -t "$SESSION:1.1" "uv run python -m backend.main" C-m
tmux send-keys -t "$SESSION:1.2" "cd classifier && uv run main.py" C-m
tmux send-keys -t "$SESSION:1.3" "uv run python -m adapters.main" C-m

# TUIs
echo "Waiting for backend..."
until curl -fsS http://localhost:8000/health >/dev/null; do
    sleep 1
done

echo "Waiting for adapter..."
until curl -fsS http://localhost:8001/health >/dev/null; do
    sleep 1
done
tmux send-keys -t "$SESSION:2" "uv run python -m backend.tui" C-m
tmux send-keys -t "$SESSION:3" "uv run python -m adapters.tui" C-m

tmux select-window -t "$SESSION:1"
tmux select-pane -t "$SESSION:1.0"

exec tmux attach -t "$SESSION"
