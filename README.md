# Evermind Demo Scaffold

Evermemos-first demo skeleton for "thought flow" visualization.

## Structure

- `apps/api`: FastAPI backend (runnable now)
- `apps/web`: Vite + React scaffold (requires Node to run)
- `packages/shared`: shared TypeScript contracts
- `docs`: product and architecture docs stubs

## Local Launch (Recommended)

1. API (terminal A)

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
/Users/northpoleforce/evermind/apps/api/.venv/bin/uvicorn app.main:app --app-dir /Users/northpoleforce/evermind/apps/api --host 127.0.0.1 --port 8000
```

2. Web (terminal B)

```bash
cd /Users/northpoleforce/evermind
npm run dev:web
```

3. Open:

- Web: `http://localhost:5173`
- API docs: `http://127.0.0.1:8000/docs`

4. Run smoke test:

```bash
cd /Users/northpoleforce/evermind
bash scripts/local_smoke_test.sh
```

## Run Backend

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then check:

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/health/evermemos`
- `GET http://localhost:8000/health/llm`

## Notes

- Node.js is required to run `apps/web`.
- Backend includes `MemoryGateway` + `EvermemosClient` with core methods:
  - `save_message`
  - `save_topic_node`
  - `query_context`
  - `rebuild_flow`

## Evermemos Integration

The backend now uses the official `evermemos` Python SDK.

- Raw chat messages are written with `memory.add(...)`
- Topic nodes are also written with `memory.add(...)` as system records
- Retrieval uses `memory.search(extra_query={"user_id": ..., "query": ...})`
- Replay reconstruction uses `memory.get(extra_query={"user_id": ...})`

## LLM Provider Setup

The API uses an OpenAI-compatible gateway layer, so you can switch providers with env vars.

- `LLM_PROVIDER=openai_compatible`
- `LLM_BASE_URL=https://api.moonshot.cn/v1` (Kimi default)
- `LLM_API_KEY=...`
- `LLM_MODEL=kimi-k2-turbo-preview`

For future providers, keep `LLM_PROVIDER=openai_compatible` and only change `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` if the provider exposes OpenAI-compatible chat completions.

Current tested local setup uses MiniMax via OpenAI-compatible mode:

- `LLM_PROVIDER=minimax`
- `LLM_BASE_URL=https://api.minimax.io/v1`
- `LLM_MODEL=MiniMax-M2` (or `MiniMax-M2.5`)
- `LLM_STRIP_THINK_TAGS=true` (recommended for clean UI output)
