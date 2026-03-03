"""
Pydantic models for API request/response validation.

These models define the CONTRACT between your API and its consumers.
FastAPI auto-generates OpenAPI/Swagger docs from these models.
"""

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Request Models
# ──────────────────────────────────────────────

class ProposalRequest(BaseModel):
    """Input for generating a B2B proposal."""

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Target company name (e.g., 'Stripe', 'Apple')",
        json_schema_extra={"examples": ["Stripe"]},
    )
    user_request: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="What the proposal should cover",
        json_schema_extra={"examples": ["Create a proposal for payment processing optimization"]},
    )
    requestor_name: str = Field(
        default="Sales Team",
        max_length=100,
        description="Who is requesting the proposal",
    )
    requestor_email: str = Field(
        default="",
        max_length=200,
        description="Optional email for the requestor",
    )


class ExportRequest(BaseModel):
    """Input for exporting a proposal to PDF/Markdown."""

    proposal_markdown: str = Field(
        ...,
        min_length=10,
        description="The proposal content in Markdown format",
    )
    company_name: str = Field(
        ...,
        min_length=1,
        description="Target company name (used in headers)",
    )
    filename: str = Field(
        default="",
        description="Custom filename (auto-generated if empty)",
    )


class ReviewRequest(BaseModel):
    """Input for resuming after human review."""

    thread_id: str = Field(..., description="The thread ID from the generate/async response")
    approved: bool = Field(default=True, description="Whether the proposal is approved")
    feedback: str = Field(default="", description="Optional feedback for revisions")


# ──────────────────────────────────────────────
# Response Models
# ──────────────────────────────────────────────

class ProposalResponse(BaseModel):
    """Full result of a proposal generation run."""

    company_name: str = ""
    industry: str = ""
    pain_points: list[str] = []
    solution_mapping: dict = {}
    proposal_draft: str = ""
    qa_score: float = 0.0
    revision_count: int = 0
    approved: bool = False
    current_phase: str = ""
    final_proposal: str = ""
    started_at: str = ""
    completed_at: str = ""

    @classmethod
    def from_state(cls, state: dict) -> "ProposalResponse":
        """Create a ProposalResponse from a ProposalState dict."""
        return cls(
            company_name=state.get("company_name", ""),
            industry=state.get("industry", ""),
            pain_points=state.get("pain_points", []),
            solution_mapping=state.get("solution_mapping", {}),
            proposal_draft=state.get("proposal_draft", ""),
            qa_score=state.get("qa_score", 0.0),
            revision_count=state.get("revision_count", 0),
            approved=state.get("approved", False),
            current_phase=state.get("current_phase", ""),
            final_proposal=state.get("final_proposal", ""),
            started_at=state.get("started_at", ""),
            completed_at=state.get("completed_at", ""),
        )


class AsyncJobResponse(BaseModel):
    """Response when starting an async proposal generation."""

    thread_id: str
    status: str = "started"
    message: str = "Proposal generation started in background"


class ProposalStatusResponse(BaseModel):
    """Status of an async proposal job."""

    thread_id: str
    status: str  # "running", "completed", "failed"
    current_phase: str = ""
    company_name: str = ""
    qa_score: float = 0.0
    revision_count: int = 0
    approved: bool = False
    error: str = ""


class ExportResponse(BaseModel):
    """Response after exporting a proposal."""

    filename: str
    filepath: str
    size_bytes: int
    format: str  # "pdf", "html", "markdown"
    message: str = ""


class HealthResponse(BaseModel):
    """API health check response."""

    status: str = "healthy"
    version: str = "1.0.0"
    api_keys: dict = {}
    requests_remaining: int = 0
    components: dict = {}


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    detail: str = ""
    status_code: int = 500
