"""FastAPI application for the B2B Proposal Generator."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.config import ProposalConfig, RuntimeConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistent knowledge data without preventing API startup on failure."""
    print("\n" + "═" * 60)
    print("  B2B PROPOSAL GENERATOR API — Starting")
    print("═" * 60)

    app.state.rag_ready = False
    app.state.rag_error = ""
    app.state.rag_document_count = 0

    if RuntimeConfig.AUTO_INGEST:
        try:
            from src.rag.ingest import ensure_documents_ingested

            count = await asyncio.to_thread(ensure_documents_ingested)
            app.state.rag_document_count = count
            app.state.rag_ready = count > 0
            print(f"  Knowledge base ready: {count} chunks")
        except Exception as exc:
            app.state.rag_error = str(exc)
            print(f"  Knowledge base initialization failed: {exc}")
    else:
        app.state.rag_error = "Automatic ingestion is disabled"
        print("  Knowledge base auto-ingestion disabled")

    print("  API health: /health")
    print("  Readiness:  /health/ready")
    print("  Liveness:   /health/live")
    print("═" * 60 + "\n")
    yield
    print("\n  API server shutting down...\n")


app = FastAPI(
    title="B2B Proposal Generator API",
    description="Multi-agent AI system for generating B2B proposals",
    version="1.1.0",
    lifespan=lifespan,
)

allowed_origins = list(RuntimeConfig.CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# API routes must be registered before the catch-all static frontend mount.
app.include_router(router)


@app.get("/health/live", tags=["System"])
async def liveness():
    """Minimal process liveness probe for container orchestrators."""
    return {"status": "alive", "version": "1.1.0"}


if RuntimeConfig.FRONTEND_STATIC_DIR.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(RuntimeConfig.FRONTEND_STATIC_DIR), html=True),
        name="frontend",
    )
else:
    @app.get("/", tags=["System"])
    async def root():
        return {
            "name": "B2B Proposal Generator API",
            "version": "1.1.0",
            "company": ProposalConfig.YOUR_COMPANY_NAME,
            "docs": "/docs",
        }
