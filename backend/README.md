# TellMom Backend

FastAPI service for chat ingest, parent auth, child account management, and real-time alerts.

## Setup

```bash
# Start PostgreSQL
docker compose up -d

# Install dependencies (from backend/)
uv sync

# Run API
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Environment

| Variable | Default |
|----------|---------|
| `DATABASE_URL` | `postgresql://tellmom:tellmom@localhost:5432/tellmom` |
| `JWT_SECRET` | `change-me-in-production` |
| `COLAB_TCP_HOST` | `localhost` |
| `COLAB_TCP_PORT` | `9999` |
| `CORS_ORIGINS` | `http://localhost:5173` |
| `GROQ_API_KEY` | *(required for LLM grooming analysis)* |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |

## API overview

- `POST /api/auth/register` — parent registration
- `POST /api/auth/login` — returns JWT
- `GET /api/auth/me` — current parent (Bearer token)
- `GET/POST/PUT/DELETE /api/children` — manage child platform accounts
- `GET /api/alerts` — list alerts for authenticated parent
- `POST /api/alerts/{id}/acknowledge` — acknowledge alert
- `WS /api/alerts/ws?token=...` — live alert stream
- `POST /api/ingest` — ingest chat batch (`platform`, `server_id`, `chat_group`)

When a user is flagged during ingest, all parents with registered children in the same chat group are notified via WebSocket and persisted alerts.
