"""
FastAPI Application Factory for the B2B Proposal Generator.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.config import ProposalConfig


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run on startup and shutdown."""
    print("\n" + "═" * 60)
    print("  🚀 B2B PROPOSAL GENERATOR API — Starting")
    print("═" * 60)
    print(f"  📄 Docs:    http://localhost:8000/docs")
    print(f"  ❤️  Health:  http://localhost:8000/health")
    print("═" * 60 + "\n")
    yield
    print("\n  👋 API Server shutting down...\n")


app = FastAPI(
    title="B2B Proposal Generator API",
    description="Multi-agent AI system for generating B2B proposals",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/", tags=["System"])
async def root():
    return {
        "name": "B2B Proposal Generator API",
        "version": "1.0.0",
        "company": ProposalConfig.YOUR_COMPANY_NAME,
        "docs": "/docs",
    }
