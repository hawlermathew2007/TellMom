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
| `CORS_ORIGINS` | `http://localhost:5173` |
| `GROQ_API_KEY` | *(required for LLM grooming analysis)* |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `CLASSIFIER_MIN_MESSAGES` | `7` |
| `CLASSIFIER_PASSWORD` | `1234` |

## API overview

- `POST /api/auth/register` — parent registration
- `POST /api/auth/login` — returns JWT
- `GET /api/auth/me` — current parent (Bearer token)
- `GET/POST/PUT/DELETE /api/children` — manage child platform accounts
- `GET /api/alerts` — list alerts for authenticated parent
- `POST /api/alerts/{id}/acknowledge` — acknowledge alert
- `WS /api/alerts/ws?token=...` — live alert stream
- `POST /api/ingest` — ingest a single message (`platform`, `user_id`, `server_id`, `message`). Messages are cached and stored in PostgreSQL. The classifier runs only once a server has at least `CLASSIFIER_MIN_MESSAGES` messages; requests are queued so only one classification runs at a time.

When a user is flagged during ingest, all parents with registered children in the same chat group are notified via WebSocket and persisted alerts.
