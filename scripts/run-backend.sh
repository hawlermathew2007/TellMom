#!/usr/bin/env bash

set -e

SESSION="dev"

# Setup
uv sync

docker compose up -d

echo "Waiting for containers to start..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q postgres)")" = "healthy" ]; do
    sleep 1
done

echo "Database is ready."

sh ./scripts/create-db.sh

# Create session if it doesn't exist
if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    tmux new-session -d -s "$SESSION"
fi

# Create window 1 if it doesn't exist
if ! tmux list-windows -t "$SESSION" | grep -q "^1:"; then
    tmux new-window -t "$SESSION":1
fi

# Remove anything already in window 1
tmux kill-pane -a -t "$SESSION":1 2>/dev/null || true

# Make a 2x2 grid
tmux split-window -h -t "$SESSION":1       # left | right
tmux split-window -v -t "$SESSION":1.0     # split left
tmux split-window -v -t "$SESSION":1.1     # split right
tmux select-layout -t "$SESSION":1 tiled

# Top-left
tmux send-keys -t "$SESSION":1.0 "uv run python -m proxy.main" C-m

# Top-right
tmux send-keys -t "$SESSION":1.1 "uv run python -m backend.main" C-m

# Bottom-left
tmux send-keys -t "$SESSION":1.2 "cd classifier && uv run main.py" C-m

# Bottom-right
tmux send-keys -t "$SESSION":1.3 "cd frontend && npm run dev" C-m

tmux select-window -t "$SESSION":1
tmux select-pane -t "$SESSION":1.0
tmux attach -t "$SESSION"
