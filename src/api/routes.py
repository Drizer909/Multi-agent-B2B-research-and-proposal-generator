"""
FastAPI Router — All REST API endpoints for the B2B Proposal Generator.

Endpoints:
    GET  /health                      — System health check
    POST /proposal/generate           — Generate proposal (synchronous, blocks 2-5 min)
    POST /proposal/generate/async     — Start async generation (returns immediately)
    GET  /proposal/status/{thread_id} — Check async job status
    GET  /proposal/result/{thread_id} — Get completed async result
    POST /proposal/export/pdf         — Export to PDF (or HTML fallback)
    POST /proposal/export/markdown    — Export to Markdown
    GET  /proposal/export/download/{filename} — Download exported file
"""

import asyncio
import time
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.api.models import (
    AsyncJobResponse,
    ErrorResponse,
    ExportRequest,
    ExportResponse,
    HealthResponse,
    ProposalRequest,
    ProposalResponse,
    ProposalStatusResponse,
)
from src.api.pdf_export import (
    export_to_html,
    export_to_markdown,
    export_to_pdf,
    get_export_capabilities,
)
from src.config import APIKeys, StorageConfig, rate_limiter

router = APIRouter()


# ══════════════════════════════════════════════
# In-Memory Job Store (for async generation)
# ══════════════════════════════════════════════

# Structure: { thread_id: { "status": "...", "result": {...}, "error": "..." } }
_jobs: dict[str, dict] = {}


# ══════════════════════════════════════════════
# GET /health — Health Check
# ══════════════════════════════════════════════

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System health check",
    tags=["System"],
)
async def health_check():
    """
    Check API health, API key status, and rate limit remaining.
    """
    api_keys = APIKeys.validate()
    capabilities = get_export_capabilities()

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        api_keys=api_keys,
        requests_remaining=rate_limiter.requests_remaining_today,
        components={
            "llm": "active" if api_keys.get("openrouter") else "not configured",
            "search": "tavily" if api_keys.get("tavily") else "not configured",
            "vector_db": "chromadb",
            "export_pdf": capabilities["pdf"],
            "export_html": capabilities["html"],
        },
    )


# ══════════════════════════════════════════════
# POST /proposal/generate — Synchronous Generation
# ══════════════════════════════════════════════

@router.post(
    "/proposal/generate",
    response_model=ProposalResponse,
    summary="Generate a B2B proposal (synchronous — takes 2-5 minutes)",
    tags=["Proposal"],
    responses={
        500: {"model": ErrorResponse, "description": "Pipeline error"},
    },
)
async def generate_proposal(request: ProposalRequest):
    """
    Run the full proposal pipeline synchronously.

    ⚠️ This endpoint BLOCKS for 2-5 minutes while the pipeline runs.
    For non-blocking usage, use POST /proposal/generate/async instead.
    """
    try:
        from src.graph.workflow import run_proposal

        # Run the blocking pipeline in a thread to not block the event loop
        result = await asyncio.to_thread(
            run_proposal,
            company_name=request.company_name,
            user_request=request.user_request,
            requestor_name=request.requestor_name,
        )

        if result.get("error"):
             raise HTTPException(status_code=500, detail=result["error"])

        return ProposalResponse.from_state(result)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Proposal generation failed: {str(e)}",
        )


# ══════════════════════════════════════════════
# POST /proposal/generate/async — Async Generation
# ══════════════════════════════════════════════

def _run_pipeline_job(thread_id: str, company_name: str, user_request: str, requestor_name: str):
    """Background function that runs the pipeline and updates the job store."""
    try:
        from src.graph.workflow import run_proposal

        _jobs[thread_id]["status"] = "running"

        result = run_proposal(
            company_name=company_name,
            user_request=user_request,
            requestor_name=requestor_name,
        )

        if result.get("error"):
            _jobs[thread_id]["status"] = "failed"
            _jobs[thread_id]["error"] = result["error"]
        else:
            _jobs[thread_id]["status"] = "completed"
            _jobs[thread_id]["result"] = result

    except Exception as e:
        _jobs[thread_id]["status"] = "failed"
        _jobs[thread_id]["error"] = str(e)
        traceback.print_exc()


@router.post(
    "/proposal/generate/async",
    response_model=AsyncJobResponse,
    summary="Start proposal generation in background",
    tags=["Proposal"],
)
async def generate_proposal_async(request: ProposalRequest):
    """
    Start proposal generation in the background.
    """
    safe_name = request.company_name.lower().replace(" ", "_").replace("/", "_")
    thread_id = f"async_{safe_name}_{int(time.time())}"

    _jobs[thread_id] = {
        "status": "queued",
        "company_name": request.company_name,
        "result": None,
        "error": "",
        "started_at": time.time(),
    }

    # Run in background
    asyncio.get_event_loop().run_in_executor(
        None,
        _run_pipeline_job,
        thread_id,
        request.company_name,
        request.user_request,
        request.requestor_name,
    )

    return AsyncJobResponse(
        thread_id=thread_id,
        status="started",
        message=f"Proposal generation for '{request.company_name}' started.",
    )


# ══════════════════════════════════════════════
# GET /proposal/status/{thread_id} — Job Status
# ══════════════════════════════════════════════

@router.get(
    "/proposal/status/{thread_id}",
    response_model=ProposalStatusResponse,
    summary="Check async proposal job status",
    tags=["Proposal"],
)
async def get_proposal_status(thread_id: str):
    """Check the status of a background proposal generation job."""
    if thread_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[thread_id]
    result = job.get("result") or {}

    return ProposalStatusResponse(
        thread_id=thread_id,
        status=job["status"],
        current_phase=result.get("current_phase", "") if isinstance(result, dict) else "",
        company_name=job.get("company_name", ""),
        qa_score=result.get("qa_score", 0.0) if isinstance(result, dict) else 0.0,
        revision_count=result.get("revision_count", 0) if isinstance(result, dict) else 0,
        approved=result.get("approved", False) if isinstance(result, dict) else False,
        error=job.get("error", ""),
    )


# ══════════════════════════════════════════════
# GET /proposal/result/{thread_id} — Full Result
# ══════════════════════════════════════════════

@router.get(
    "/proposal/result/{thread_id}",
    response_model=ProposalResponse,
    summary="Get completed proposal result",
    tags=["Proposal"],
)
async def get_proposal_result(thread_id: str):
    """Get the full result of a completed proposal generation job."""
    if thread_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = _jobs[thread_id]

    if job["status"] in ["running", "queued"]:
        raise HTTPException(status_code=202, detail=f"Job still {job['status']}")

    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=f"Job failed: {job.get('error')}")

    result = job.get("result", {})
    return ProposalResponse.from_state(result)


# ══════════════════════════════════════════════
# POST /proposal/export/pdf — PDF Export
# ══════════════════════════════════════════════

@router.post(
    "/proposal/export/pdf",
    summary="Export proposal to PDF (or HTML fallback)",
    tags=["Export"],
)
async def export_pdf(request: ExportRequest):
    """Export a proposal to PDF format."""
    try:
        filepath, size = await asyncio.to_thread(
            export_to_pdf,
            markdown_text=request.proposal_markdown,
            company_name=request.company_name,
            filename=request.filename,
        )

        filename = Path(filepath).name
        media_type = "application/pdf" if filepath.endswith(".pdf") else "text/html"

        return FileResponse(path=filepath, filename=filename, media_type=media_type)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


# ══════════════════════════════════════════════
# POST /proposal/export/html — HTML Export
# ══════════════════════════════════════════════

@router.post(
    "/proposal/export/html",
    summary="Export proposal to styled HTML",
    tags=["Export"],
)
async def export_html(request: ExportRequest):
    """Export a proposal to a styled HTML file."""
    try:
        filepath, size = await asyncio.to_thread(
            export_to_html,
            markdown_text=request.proposal_markdown,
            company_name=request.company_name,
            filename=request.filename,
        )
        return FileResponse(path=filepath, filename=Path(filepath).name, media_type="text/html")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HTML export failed: {str(e)}")


# ══════════════════════════════════════════════
# POST /proposal/export/markdown — Markdown Export
# ══════════════════════════════════════════════

@router.post(
    "/proposal/export/markdown",
    summary="Export proposal to Markdown file",
    tags=["Export"],
)
async def export_md(request: ExportRequest):
    """Export a proposal as a Markdown .md file."""
    try:
        filepath, size = await asyncio.to_thread(
            export_to_markdown,
            markdown_text=request.proposal_markdown,
            company_name=request.company_name,
            filename=request.filename,
        )
        return FileResponse(path=filepath, filename=Path(filepath).name, media_type="text/markdown")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Markdown export failed: {str(e)}")


# ══════════════════════════════════════════════
# GET /proposal/export/download/{filename} — Download
# ══════════════════════════════════════════════

@router.get(
    "/proposal/export/download/{filename}",
    summary="Download a previously exported file",
    tags=["Export"],
)
async def download_file(filename: str):
    """Download an exported file from the output directory."""
    filepath = StorageConfig.OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")

    suffix = filepath.suffix.lower()
    media_types = {".pdf": "application/pdf", ".html": "text/html", ".md": "text/markdown"}
    return FileResponse(path=str(filepath), filename=filename, media_type=media_types.get(suffix, "application/octet-stream"))


# ══════════════════════════════════════════════
# GET /proposal/export/formats — Available Formats
# ══════════════════════════════════════════════

@router.get(
    "/proposal/export/formats",
    summary="List available export formats",
    tags=["Export"],
)
async def list_export_formats():
    """Check which export formats are available on this system."""
    capabilities = get_export_capabilities()
    return {"formats": capabilities}
