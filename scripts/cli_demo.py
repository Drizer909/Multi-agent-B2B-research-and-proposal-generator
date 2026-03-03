"""
CLI Demo — Interactive B2B Proposal Generator.

Showcases the power of multi-agent orchestration with LangGraph.
"""

import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def print_banner():
    print("\n")
    print("═" * 60)
    print("  🚀 B2B PROPOSAL GENERATOR — Interactive Demo")
    print("  Orchestrated by LangGraph")
    print("═" * 60)

def main():
    from src.graph import run_proposal, run_proposal_with_review, resume_after_review
    from src.config import StorageConfig
    
    print_banner()
    
    # 1. Inputs
    print("\n📋 PROSPECT DETAILS:")
    company = input("   Company name: ").strip() or "Stripe"
    request = input("   What are we solving? (e.g., churn, fraud): ").strip() or "Onboarding optimization and churn reduction"
    
    print("\n💡 MODE SELECTION:")
    print("   [1] Full Auto (Continuous flow)")
    print("   [2] Human Review (Pauses for your input)")
    mode = input("   Choice: ").strip() or "1"
    
    # 2. Execution
    if mode == "1":
        print("\n🏁 Starting FULL AUTO run...")
        final_state = run_proposal(company, request)
    else:
        print("\n🏁 Starting HUMAN REVIEW run...")
        app, config = run_proposal_with_review(company, request)
        
        # Get proposal draft from state to show it
        snapshot = app.get_state(config)
        draft = snapshot.values.get("proposal_draft", "No draft generated.")
        
        print("\n" + "📄" * 30)
        print("  PROPOSAL DRAFT PREVIEW (First 500 chars):")
        print("  " + draft[:500].replace("\n", "\n  ") + "...")
        print("📄" * 30)
        
        choice = input("\n✅ Approved? (y/n): ").strip().lower()
        feedback = ""
        if choice != "y":
            feedback = input("💬 Feedback (what to change?): ").strip()
            
        final_state = resume_after_review(app, config, approved=(choice=="y"), feedback=feedback)
        
    # 3. Output
    print("\n" + "🏁" * 30)
    print("  DEMO COMPLETE")
    print("🏁" * 30)
    
    proposal = final_state.get("final_proposal", final_state.get("proposal_draft", ""))
    if proposal:
        out_file = StorageConfig.OUTPUT_DIR / f"{company.lower()}_proposal.md"
        StorageConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file.write_text(proposal)
        print(f"\n💾 Saved final proposal to: {out_file}")
    
    print("\nThank you for using B2B Proposal Generator!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error in demo: {e}")
        import traceback
        traceback.print_exc()
