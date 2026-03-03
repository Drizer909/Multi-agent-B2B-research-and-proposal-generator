"""
ProposalState — The shared memory object for the entire multi-agent pipeline.

This file is MODEL-AGNOSTIC. It works the same whether you use
GPT-4o, Llama 3.3, Claude, or any other LLM.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages


# ──────────────────────────────────────────────
# Sub-Schemas
# ──────────────────────────────────────────────


class ResearchData(TypedDict, total=False):
    """Output from the Research Agent."""

    company_overview: str
    industry: str
    employee_count: str
    headquarters: str
    founded_year: str
    recent_news: list[str]
    competitors: list[str]
    technologies_used: list[str]
    funding_info: str
    key_challenges: list[str]
    growth_signals: list[str]
    risk_factors: list[str]
    sources: list[str]


class SolutionMapping(TypedDict, total=False):
    """Output from the Analysis Agent."""

    pain_to_solution: dict[str, str]
    pain_to_case_studies: dict[str, list[str]]
    fit_score: float
    fit_summary: str
    recommended_package: str
    estimated_timeline: str
    estimated_value: str


class QAResult(TypedDict, total=False):
    """Output from the QA Agent."""

    overall_score: float
    section_scores: dict[str, float]
    critical_issues: list[str]
    minor_issues: list[str]
    suggestions: list[str]
    factual_accuracy: bool
    all_sections_present: bool
    professional_tone: bool
    has_specific_metrics: bool
    company_name_correct: bool


# ──────────────────────────────────────────────
# Main State
# ──────────────────────────────────────────────


class ProposalState(TypedDict, total=False):
    """
    Master state object flowing through every node in the graph.

    REDUCER RULES:
    • No annotation    → OVERWRITE (last write wins)
    • Annotated[..add] → APPEND (accumulates values)
    • add_messages      → SMART MERGE (LangChain message handling)
    """

    # ─── INPUT ──────────────────────────────────
    company_name: str
    user_request: str
    requestor_name: str
    requestor_email: str

    # ─── RESEARCH PHASE ────────────────────────
    research_data: ResearchData
    industry: str
    company_size: str
    pain_points: Annotated[list[str], operator.add]  # APPEND reducer

    # ─── ANALYSIS PHASE ────────────────────────
    matched_case_studies: list[dict[str, Any]]
    solution_mapping: SolutionMapping

    # ─── WRITING PHASE ─────────────────────────
    proposal_draft: str
    proposal_sections: dict[str, str]

    # ─── QA PHASE ──────────────────────────────
    qa_result: QAResult
    qa_score: float

    # ─── REVISION TRACKING ─────────────────────
    revision_count: int
    revision_history: Annotated[list[str], operator.add]  # APPEND reducer

    # ─── HUMAN-IN-THE-LOOP ─────────────────────
    human_feedback: str
    approved: bool
    review_requested_at: str
    review_completed_at: str

    # ─── OUTPUT ────────────────────────────────
    final_proposal: str
    pdf_path: str
    export_format: str

    # ─── AGENT MEMORY ──────────────────────────
    messages: Annotated[list, add_messages]  # SMART MERGE reducer

    # ─── METADATA ──────────────────────────────
    current_phase: str
    error: str
    started_at: str
    completed_at: str


# ──────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────


def create_initial_state(
    company_name: str,
    user_request: str,
    requestor_name: str = "Sales Team",
    requestor_email: str = "",
) -> ProposalState:
    """Create a properly initialized ProposalState."""
    from datetime import datetime, timezone

    return ProposalState(
        company_name=company_name,
        user_request=user_request,
        requestor_name=requestor_name,
        requestor_email=requestor_email,
        research_data={},
        industry="",
        company_size="",
        pain_points=[],
        matched_case_studies=[],
        solution_mapping={},
        proposal_draft="",
        proposal_sections={},
        qa_result={},
        qa_score=0.0,
        revision_count=0,
        revision_history=[],
        human_feedback="",
        approved=False,
        review_requested_at="",
        review_completed_at="",
        final_proposal="",
        pdf_path="",
        export_format="pdf",
        messages=[],
        current_phase="initialized",
        error="",
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at="",
    )


# ──────────────────────────────────────────────
# Debug Utility
# ──────────────────────────────────────────────


def print_state_summary(state: ProposalState) -> None:
    """Print a human-readable summary of the current state."""
    print()
    print("═" * 55)
    print("  PROPOSAL STATE SUMMARY")
    print("═" * 55)
    print(f"  Company:       {state.get('company_name', 'N/A')}")
    print(f"  Industry:      {state.get('industry', 'Not yet classified')}")
    print(f"  Phase:         {state.get('current_phase', 'unknown')}")
    print(f"  Pain Points:   {len(state.get('pain_points', []))} identified")

    for i, pp in enumerate(state.get("pain_points", []), 1):
        print(f"                 {i}. {pp}")

    print(f"  Case Studies:  {len(state.get('matched_case_studies', []))} matched")
    print(f"  QA Score:      {state.get('qa_score', 0.0):.1%}")
    print(f"  Revisions:     {state.get('revision_count', 0)}")
    print(f"  Approved:      {'✅ Yes' if state.get('approved') else '⏳ Pending'}")
    print(f"  Draft Length:  {len(state.get('proposal_draft', ''))} chars")
    print(f"  Messages:      {len(state.get('messages', []))} in history")
    print("═" * 55)
    print()