# Local Go-Live Checklist

## Pre-flight

- `.env` has valid keys for:
  - `EVERMEMOS_API_KEY`
  - `LLM_API_KEY`
- LLM is configured:
  - `LLM_PROVIDER=minimax`
  - `LLM_BASE_URL=https://api.minimax.io/v1`
  - `LLM_MODEL=MiniMax-M2` or `MiniMax-M2.5`
- Think tag filtering is enabled for demo UX:
  - `LLM_STRIP_THINK_TAGS=true`

## Start Services

1. Start API:
   - `cd apps/api`
   - `source .venv/bin/activate`
   - `/Users/northpoleforce/evermind/apps/api/.venv/bin/uvicorn app.main:app --app-dir /Users/northpoleforce/evermind/apps/api --host 127.0.0.1 --port 8000`
2. Start web:
   - `cd /Users/northpoleforce/evermind`
   - `npm run dev:web`

## Health Gates

- `GET /health` should return `ok=true`
- `GET /health/evermemos` should return `ok=true`
- `GET /health/llm` should return `ok=true`

## E2E Gate

- Send one message to `/chat`
- Confirm HTTP 200
- Confirm `assistant_text` is present
- Confirm `assistant_text` does not include `<think>` tags

## Demo Readiness

- Open `http://localhost:5173`
- Confirm graph node appears after sending a message
- Confirm no red errors in browser console
- Prepare a 2-3 minute scripted message sequence for stable live demo
