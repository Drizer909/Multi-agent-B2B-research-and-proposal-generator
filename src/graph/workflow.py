"""
LangGraph StateGraph Workflow — Orchestator for the B2B Proposal Pipeline.

Wires together Research, Analysis, Writing, and QA agents into a 
directed graph with persistence and conditional routing.
"""

import time
from datetime import datetime, timezone
from typing import Literal

from langgraph.graph import END, StateGraph

from src.config import ProposalConfig
from src.state.schema import ProposalState, create_initial_state, print_state_summary
from src.agents.research import research_agent
from src.agents.analysis import analysis_agent
from src.agents.writing import writing_agent
from src.agents.qa import qa_agent
from src.graph.checkpointer import get_checkpointer

# ────────────────────────────────────────────────────────
# Helper Nodes
# ────────────────────────────────────────────────────────

def increment_revision(state: ProposalState) -> dict:
    """Increment the revision counter before re-writing."""
    current_revisions = state.get("revision_count", 0)
    new_count = current_revisions + 1
    
    print("\n" + "─" * 60)
    print(f"  🔄 REVISION #{new_count} — Looping back to writing agent")
    print("─" * 60)
    
    return {
        "revision_count": new_count,
        "current_phase": f"revision_{new_count}"
    }

def human_review(state: ProposalState) -> dict:
    """
    Pause point for human review.
    
    This node serves as the terminal point for the 'draft' phase.
    The graph will interrupt BEFORE this node if configured properly.
    """
    qa_score = state.get("qa_score", 0.0)
    company_name = state.get("company_name", "Unknown Prospect")
    
    print("\n" + "═" * 60)
    print("  👤 HUMAN REVIEW — Pipeline Paused")
    print("═" * 60)
    print(f"  Prospect: {company_name}")
    print(f"  QA Score: {qa_score:.0%}")
    print("\n  Awaiting approval to finalize...")
    print("═" * 60)
    
    return {
        "current_phase": "awaiting_human_review"
    }

def finalize(state: ProposalState) -> dict:
    """Final node that stamps the proposal as complete."""
    proposal_draft = state.get("proposal_draft", "")
    
    print("\n" + "═" * 60)
    print("  🎉 FINALIZE — Proposal Workflow Complete!")
    print("═" * 60)
    
    return {
        "final_proposal": proposal_draft,
        "approved": True,
        "current_phase": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }

# ────────────────────────────────────────────────────────
# Routing Logic
# ────────────────────────────────────────────────────────

def route_after_qa(state: ProposalState) -> Literal["human_review", "increment_revision"]:
    """
    Routes based on QA score and revision limits.
    """
    qa_score = state.get("qa_score", 0.0)
    revision_count = state.get("revision_count", 0)
    
    print(f"\n  🔀 QA ROUTER: Score={qa_score:.0%} | Revision={revision_count}/{ProposalConfig.MAX_REVISIONS}")
    
    # Path 1: Auto-pass (good score) or Force-pass (too many revisions)
    if qa_score >= ProposalConfig.QA_AUTO_PASS_SCORE or revision_count >= ProposalConfig.MAX_REVISIONS:
        if qa_score < ProposalConfig.QA_AUTO_PASS_SCORE:
            print("  ⚠️ Score below threshold, but max revisions reached. Forcing to Human Review.")
        else:
            print("  ✅ QA Score passed threshold. Proceeding to Human Review.")
        return "human_review"
    
    # Path 2: Fail QA and revisions remaining — Loop back
    print("  🔄 Score below threshold. Routing back for revision.")
    return "increment_revision"

# ────────────────────────────────────────────────────────
# Graph Builder
# ────────────────────────────────────────────────────────

def _build_base_graph() -> StateGraph:
    """Builds the core StateGraph with nodes and edges."""
    workflow = StateGraph(ProposalState)
    
    # Add Nodes
    workflow.add_node("research", research_agent)
    workflow.add_node("analysis", analysis_agent)
    workflow.add_node("writing", writing_agent)
    workflow.add_node("qa", qa_agent)
    workflow.add_node("increment_revision", increment_revision)
    workflow.add_node("human_review", human_review)
    workflow.add_node("finalize", finalize)
    
    # Set Entry Point
    workflow.set_entry_point("research")
    
    # Define Edges
    workflow.add_edge("research", "analysis")
    workflow.add_edge("analysis", "writing")
    workflow.add_edge("writing", "qa")
    
    # Conditional Edges from QA
    workflow.add_conditional_edges(
        "qa",
        route_after_qa,
        {
            "human_review": "human_review",
            "increment_revision": "increment_revision"
        }
    )
    
    # Revision Loop
    workflow.add_edge("increment_revision", "writing")
    
    # Human Approval Flow
    workflow.add_edge("human_review", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow

def build_graph():
    """Compiles the graph WITH human interrupt and persistence."""
    workflow = _build_base_graph()
    checkpointer = get_checkpointer()
    
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"]
    )

def build_graph_no_interrupt():
    """Compiles the graph WITHOUT human interrupt (full auto)."""
    workflow = _build_base_graph()
    checkpointer = get_checkpointer()
    
    return workflow.compile(
        checkpointer=checkpointer
    )

# ────────────────────────────────────────────────────────
# Run Functions
# ────────────────────────────────────────────────────────

def run_proposal(company_name: str, user_request: str, requestor_name: str = "Sales Team") -> dict:
    """Runs the full pipeline in AUTO mode (no pausing)."""
    print("\n" + "🚀" * 30)
    print("  B2B PROPOSAL GENERATOR — Full Auto Mode")
    print("🚀" * 30)
    
    initial_state = create_initial_state(company_name, user_request, requestor_name)
    app = build_graph_no_interrupt()
    
    thread_id = f"proposal_{int(time.time())}"
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"\n  Starting Thread: {thread_id}")
    final_state = app.invoke(initial_state, config=config)
    
    print("\n")
    print_state_summary(final_state)
    return final_state

def run_proposal_with_review(company_name: str, user_request: str, requestor_name: str = "Sales Team"):
    """Runs the pipeline and PAUSES for human review."""
    print("\n" + "🚀" * 30)
    print("  B2B PROPOSAL GENERATOR — Human Review Mode")
    print("🚀" * 30)
    
    initial_state = create_initial_state(company_name, user_request, requestor_name)
    app = build_graph()
    
    thread_id = f"review_{int(time.time())}"
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"\n  Starting Review Thread: {thread_id}")
    
    # This will run until the interrupt before "human_review"
    for event in app.stream(initial_state, config=config):
        for node, values in event.items():
            if node != "__end__":
                print(f"  ✅ Completed Node: {node}")
                
    print("\n" + "═" * 60)
    print("  ⏸️  PIPELINE PAUSED at Human Review step.")
    print("  Thread ID:", thread_id)
    print("  Use resume_after_review(app, config) to proceed.")
    print("═" * 60)
    
    return app, config

def resume_after_review(app, config: dict, approved: bool = True, feedback: str = ""):
    """Resumes the pipeline after human interaction."""
    print("\n" + "▶️" * 30)
    print("  RESUMING PIPELINE")
    print("▶️" * 30)
    
    if feedback:
        print(f"  💬 Feedback provided: {feedback}")
        app.update_state(config, {"human_feedback": feedback})
    
    # Resume by passing None (it picks up from checkpoint)
    # We pass the result of the stream to get the final state
    final_result = None
    for event in app.stream(None, config=config):
        for node, values in event.items():
            if node != "__end__":
                print(f"  ✅ Completed Node: {node}")
                final_result = values
                
    # Get the latest state
    final_state = app.get_state(config).values
    
    print("\n")
    print_state_summary(final_state)
    return final_state
