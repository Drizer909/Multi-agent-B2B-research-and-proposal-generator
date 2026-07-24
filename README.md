# B2B Proposal Generator

A portfolio/demo application that generates personalized B2B proposals with a staged AI workflow. A Next.js frontend starts a FastAPI background job; LangGraph coordinates research, solution analysis, proposal writing, and LLM-based QA; ChromaDB supplies internal case studies and product information; Tavily supplies current web research.

## What problem it solves

Sales teams often spend hours researching prospects, finding relevant case studies, drafting proposals, and reviewing them. This project automates the first draft so a salesperson can focus on validating facts, editing the commercial offer, and speaking with the customer.

> Important: generated proposals are drafts, not verified business documents. A person should check company facts, claims, prices, and ROI figures before sending them.

## Architecture

```text
Browser (Next.js + React + TypeScript)
  -> FastAPI REST API
  -> background job in the API process
  -> LangGraph shared state
       Research -> Analysis -> Writing -> QA
                                 ^        |
                                 |-- revise when score < 90% (maximum 3 revisions)
       -> Human-review node in auto mode -> Finalize
  -> Markdown result
  -> optional PDF, HTML, or Markdown export
```

The four "agents" are specialized LangGraph node functions with separate prompts. They run in a fixed sequence; they are not independent servers and the LLM does not dynamically choose the next tool.

### Data sources

- **External research:** Tavily web and news search.
- **Internal knowledge:** Markdown files under `data/` are split into chunks, converted to embeddings, and stored in ChromaDB.
- **Language model:** OpenRouter's OpenAI-compatible API, configured through `LLM_MODEL`.
- **Persistence:** LangGraph checkpoints are saved in SQLite. API background jobs are currently held in process memory and are lost when the API restarts.

## Tech stack

### Backend

- **Python 3.10+** — backend programming language.
- **FastAPI** — framework that defines the REST API and generates Swagger/OpenAPI documentation.
- **Uvicorn** — ASGI server that runs FastAPI.
- **Pydantic** — validates API request and response data.
- **LangGraph** — models the agent workflow as nodes, edges, shared state, and conditional routes.
- **LangChain** — common interfaces for LLM messages, tools, embeddings, and documents.
- **OpenRouter via `ChatOpenAI`** — sends chat requests through an OpenAI-compatible endpoint.
- **Tavily** — web-search API used by the research step.
- **Hugging Face sentence-transformers** — runs `all-MiniLM-L6-v2` locally to create text embeddings.
- **ChromaDB** — local vector database used for semantic retrieval.
- **SQLite** — file-based database used for LangGraph checkpoints.
- **WeasyPrint** — converts styled HTML into PDF when its operating-system libraries are available.

### Frontend

- **Next.js 14 App Router** — React framework and application router.
- **React 18** — component-based user-interface library.
- **TypeScript** — JavaScript with static type checking.
- **Tailwind CSS** — utility-class CSS framework.
- **PostCSS and Autoprefixer** — process CSS and add browser-specific prefixes.
- **Lucide React** — icon component library.

### Infrastructure

- **Docker** — packages the Python API and required system libraries into a container.
- **Environment variables** — supply secrets and deployment-specific configuration without committing them to Git.

## Local setup

### 1. Backend

```bash
# From the repository root
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY and TAVILY_API_KEY.

# Build the local vector knowledge base. This is required initially
# and whenever files under data/ change.
python -m src.rag.ingest

# Run the API without development auto-reload.
python scripts/run_api.py --no-reload
```

Verify the API:

- API root: `http://localhost:8000/`
- Health/configuration status: `http://localhost:8000/health`
- Interactive Swagger documentation: `http://localhost:8000/docs`

The health endpoint reports whether keys are configured; it does not perform live calls to OpenRouter, Tavily, or ChromaDB.

### 2. Frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Visit `http://localhost:3000`. The frontend uses `/api` by default, and the configured Next.js rewrite proxies that path to `http://localhost:8000`. This default is intended for local development; production should set `NEXT_PUBLIC_API_URL`.

### 3. Generate a proposal

1. Enter the target company.
2. Describe the problem or solution the proposal should cover.
3. Optionally enter the requestor name.
4. Select **Generate Proposal** and wait for the job to complete.
5. Review all facts and commercial claims.
6. Export the result as PDF, HTML, or Markdown.

## Verification commands

Run these after installing dependencies and configuring the environment:

```bash
python scripts/verify_phase1.py
python scripts/verify_phase2.py
python scripts/verify_phase3.py --tools-only
python scripts/verify_phase4.py --structure-only
python scripts/verify_phase5.py
cd frontend && npm run build
```

The repository's `verify_phase*.py` files are smoke checks, not a complete automated test suite. Some checks call paid or rate-limited external services.

## Deployment

The frontend and Python backend must both be reachable:

1. Deploy the FastAPI/Docker service to a platform that supports long-running Python requests and persistent storage.
2. Set backend secrets: `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, and optional model/storage settings.
3. Set `CORS_ORIGINS` on the backend to the frontend URL. Use commas for multiple origins.
4. Deploy `frontend/` and set `NEXT_PUBLIC_API_URL` to the public backend URL, for example `https://api.example.com`.
5. Rebuild the frontend after changing `NEXT_PUBLIC_API_URL`; it is a public build-time variable.
6. Test `<backend-url>/health`, submit one proposal, poll its status, fetch its result, and test every export format.

A Vercel frontend alone is not enough: without `NEXT_PUBLIC_API_URL`, the deployed Next.js server will try to proxy API requests to its own `localhost:8000`, where this Python backend is not normally running. This repository does not contain a public deployment URL, so deployment health must be checked using the URL from the hosting dashboard.

## Current limitations

- API background jobs are in memory and are not durable across restarts or multiple workers.
- SQLite checkpoints and API job IDs are separate; the HTTP API does not expose checkpoint resume.
- Human-review pause/resume exists in the Python workflow helper but is not connected to API or frontend endpoints.
- Polling reports job-level status, not true node-by-node live progress.
- QA is an LLM review, not independent factual verification.
- RAG retrieval does not enforce citations in the final proposal.
- Authentication, authorization, durable queues, observability, and conventional regression tests are not yet implemented.

## Interview summary

> "I built a full-stack B2B proposal generator. Next.js provides the typed frontend, FastAPI exposes asynchronous proposal and export endpoints, and LangGraph orchestrates four specialized AI stages over shared state. The research stage combines Tavily with an internal ChromaDB knowledge base; analysis maps prospect pain points to products and case studies; writing produces a structured Markdown proposal; and QA conditionally sends weak drafts back for up to three targeted revisions. SQLite stores graph checkpoints, while WeasyPrint handles PDF export. I would describe it as a working prototype and would next replace the in-memory job store with a durable queue, expose real checkpoint-based human review, enforce citations, and add automated tests and production authentication."

## Roadmap

- Durable jobs with Redis/Celery, a database, or a managed workflow service.
- API/frontend human approval and rejection flow.
- Real intermediate progress events through WebSockets or Server-Sent Events.
- Deterministic validation, citations, and source provenance.
- DOCX/PPTX export and section-level rewrites.
- Automated backend/frontend tests and CI.
