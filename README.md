# VyaparFlow

Voice-first Agentic Business Operating System for micro/small enterprises.

## Stack
- **Frontend**: React / Next.js + TypeScript
- **Backend**: FastAPI + Python (async)
- **Database**: PostgreSQL (+ pgvector for RAG)
- **Cache/Queue**: Redis
- **Agent Layer**: LangGraph + LLM + Whisper + IndicTrans2 + TTS

## Repo layout
```
vyaparflow/
  apps/
    web/          # Next.js frontend (scaffolded in a later step)
    api/          # FastAPI backend
  infra/
    docker/       # docker-compose, Dockerfiles
  docs/           # design docs
```

## Local dev (backend)
```bash
cd apps/api
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# start Postgres + Redis
docker compose -f ../../infra/docker/docker-compose.yml up -d

# run migrations
alembic upgrade head

# run the API
uvicorn app.main:app --reload
```

API docs will be available at `http://localhost:8000/docs`.

## Build steps (tracked)
1. ✅ Repo scaffold + DB schema/migrations
2. ⬜ Auth + tenant/business context
3. ⬜ Core domain: Products/Inventory/Finance/Transactions
4. ⬜ Voice command lifecycle (text input first)
5. ⬜ NLP parsing layer
6. ⬜ LangGraph Supervisor + Agent tool registry
7. ⬜ Analytics, reminders, audit
8. ⬜ RAG pipeline (ingestion, embeddings, retrieval)
9. ⬜ Voice pipeline (Whisper, IndicTrans2, TTS)
10. ⬜ Frontend (Next.js)
