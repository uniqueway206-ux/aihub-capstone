# AIHub: Multi-Agent AI Assistant

Capstone project for the **Enablers AI Engineer** program. One platform that chats with your PDFs (RAG), queries a SQL database in plain English, searches the web, and summarises web pages / YouTube videos. A LangGraph router decides which agent handles each message.

```
 Streamlit UI ──HTTP──▶ Flask REST API ──▶ Services ──▶ LangGraph agent
                         (auth, limits,                    │ router
                          validation)                      ├─ rag       FAISS + HF embeddings + Groq
                                                           ├─ sql       NL→SQL, read-only SQLite
                                                           ├─ web       DuckDuckGo + LLM answer
                                                           ├─ summarize web page / YouTube (map-reduce)
                                                           └─ chat      memory-aware general chat
```

## Course outline coverage

| Module | Where it shows up |
|---|---|
| 1. Python for AI builders | Modular package (`src/aihub`), OOP services, error handling, file handling, Streamlit UI (`ui/streamlit_app.py`) |
| 2. ML/DL foundations | Embeddings (sentence-transformers / transformer encoder) power retrieval |
| 3. GenAI & LangChain | `llm.py` provider factory, prompt templates, LCEL chains (`rag/chain.py`) |
| 4. Real-world GenAI | Chat memory (`memory.py`), PDF RAG with Groq, SQL chat, summariser, search agent |
| 5. Advanced integrations | Vector DB (FAISS), tools/agents, Streamlit deployment, Docker for cloud |
| 6. LangGraph | Stateful multi-agent router (`agents/graph.py`) |
| 7. Flask for AI deployment | REST API, file upload handling, gunicorn, Docker (`api/app.py`) |

## Production features

- Config via environment (pydantic-settings), no secrets in code
- Input validation, JSON error handling, request size limit, rate limiting, optional `X-API-Key` auth
- PDF upload checks (extension + magic bytes + sanitised filename)
- SQL safety in 4 layers: prompt, static validator, **read-only DB connection**, row limit
- SSRF protection on URL summarisation (public hosts only, no redirects, size cap)
- Bounded, thread-safe session memory
- Lazy loading, so `/health` and tests need no API key or model downloads
- 27 unit tests, ruff linting, GitHub Actions CI, non-root Docker image with healthcheck

## Quick start

```bash
git clone <your-repo-url> && cd aihub-capstone
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                    # add GROQ_API_KEY (free at console.groq.com)
python scripts/seed_demo_db.py                          # demo data for SQL chat

# terminal 1
PYTHONPATH=src flask --app "aihub.api.app:app_factory" run --port 8000
# terminal 2
PYTHONPATH=src streamlit run src/aihub/ui/streamlit_app.py
```

Windows PowerShell: set `$env:PYTHONPATH="src"` before each command.

Docker: `cp .env.example .env`, add the key, then `docker compose up --build` → UI at http://localhost:8501, API at http://localhost:8000.

## API

| Method | Path | Body |
|---|---|---|
| GET | `/health` | none |
| POST | `/api/chat` | `{"message": "...", "session_id": "optional"}` |
| DELETE | `/api/chat/<session_id>` | resets memory |
| POST | `/api/documents` | multipart `file` (PDF) |
| GET / DELETE | `/api/documents` | list / clear index |
| POST | `/api/summarize` | `{"url": "..."}` |
| POST | `/api/sql` | `{"question": "..."}` |

```bash
curl -X POST localhost:8000/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"Which city has the most customers?"}'
```

## Tests

```bash
PYTHONPATH=src pytest -q --cov=aihub
```

## Push to GitHub

```bash
git init && git add . && git commit -m "AIHub capstone"
git branch -M main
git remote add origin https://github.com/<you>/aihub-capstone.git
git push -u origin main
```
Check `git status` first: `.env` must not appear (it is git-ignored).

## Ideas to extend (good talking points for interviews)

- Swap `SessionStore` for Redis; swap FAISS for AstraDB/pgvector (Module 5)
- Add a CrewAI research crew or Hugging Face Spaces deployment
- Fine-tune a small model (Module 6) and add it as another LangGraph route
- Streaming responses and an evaluation set for RAG answers
