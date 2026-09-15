# HOMELANDER

A free, local-first, open-source personal AI assistant. No paid APIs, no
cloud model required — HOMELANDER talks to a local Ollama instance running
on your own machine, so your conversations, files, and memory never leave
your computer unless you explicitly turn on web search.

## Status

This is being built incrementally. **Currently implemented (Phase 1–2):**

- Full project structure (frontend/backend/data/scripts/tests)
- SQLite database with the complete schema (users, conversations, messages,
  projects, files, documents, chunks, knowledge_collections, memories,
  settings, research_sessions)
- `ModelProvider` abstraction + working `OllamaProvider` (real HTTP calls to
  Ollama's REST API — list models, health check, streaming chat generation,
  pull/delete models)
- FastAPI backend with:
  - `GET  /api/health`
  - `GET  /api/models` — live status + installed models per provider
  - `POST /api/models/pull` — streamed model download progress
  - `DELETE /api/models/{provider}/{model}`
  - `POST /api/chat` — streams a real chat completion via Server-Sent Events,
    persists user + assistant messages, creates conversations automatically
  - `GET/PATCH/DELETE /api/chat/conversations...` — history management
  - Global error handler that never leaks stack traces to the client, and a
    friendly "start Ollama and try again" message when the engine is offline

**Not yet built** (coming in the next phases, per the original spec):
frontend UI, web research, deep research mode, file/PDF/DOCX/XLSX ingestion,
RAG + vector store, image understanding, coding mode helpers, voice
input/output, memory extraction, projects UI, settings UI, calculator tool,
sandboxed code execution, tests, install scripts.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- Node.js 18+ (once the frontend is added)

## Setup (current backend-only state)

```bash
cd homelander
cp .env.example .env
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Then in another terminal, make sure Ollama is running and has a model:

```bash
ollama serve          # if not already running
ollama pull llama3.1:8b
```

Check it's alive:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/models
```

Send a message:

```bash
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"hello","model":"llama3.1:8b","provider":"ollama"}'
```

## Architecture

```
Frontend (React, not yet built)
    ↓
FastAPI (backend/main.py)
    ↓
API routes (backend/api/*)
    ↓
Model Provider Registry (backend/models/registry.py)
    ↓
OllamaProvider  (backend/models/ollama_provider.py)  → local Ollama daemon
LocalProvider   (future)
```

No feature in this codebase is a stub that just says "coming soon" — every
route above does a real operation against a real local database or a real
local model runtime, and reports an honest error if that runtime isn't
available.
