# TellMom Frontend

Minimal parent dashboard. API client is generated from the FastAPI OpenAPI schema.

## Setup

```bash
# Start backend first, then generate the typed client
npm install
npm run generate-api

npm run dev
```

The app proxies `/api` to `http://localhost:8000` during development.

After running `generate-api`, import services from `./src/apis` via the helpers in `./src/apis/client.ts`.
