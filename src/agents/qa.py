"""
QA Agent — Reviews and scores the generated proposal.

Takes a proposal_draft and validates it against quality criteria:
1. All required sections present
2. Professional tone
3. Specific metrics included
4. Company name used correctly
5. Factual accuracy (cross-checks with research data)

Flow:
    proposal_draft → QA Agent → qa_result, qa_score
"""

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import ModelConfig, ProposalConfig, OpenRouterRateLimiter
from src.state.schema import ProposalState, QAResult

# Initialize rate limiter
rate_limiter = OpenRouterRateLimiter()

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

QA_SYSTEM_PROMPT = """You are an expert B2B proposal quality analyst. Your job is to review a business proposal and provide a detailed quality assessment.

EVALUATION CRITERIA:

1. **Section Completeness** (0.0-1.0): Are all required sections present and substantive?
   Required sections: {sections}

2. **Professional Tone** (true/false): Is the language professional, confident, and appropriate?

3. **Specific Metrics** (true/false): Does the proposal include specific numbers, percentages, timelines?

4. **Company Name Correct** (true/false): Is the prospect's company name ({prospect_name}) used correctly throughout?

5. **Factual Accuracy** (true/false): Do the claims align with the research data provided?

6. **Section Quality** (0.0-1.0 per section): Rate each section individually.

SCORING GUIDE:
- 0.9-1.0: Excellent — ready to send
- 0.7-0.89: Good — minor revisions needed
- 0.5-0.69: Fair — significant revisions needed
- Below 0.5: Poor — major rewrite needed

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{{
    "overall_score": 0.85,
    "section_scores": {{
        "Executive Summary": 0.9,
        "Understanding Your Challenges": 0.8,
        ...
    }},
    "critical_issues": ["issue that must be fixed before sending"],
    "minor_issues": ["nice-to-have improvement"],
    "suggestions": ["specific suggestion for improvement"],
    "factual_accuracy": true,
    "all_sections_present": true,
    "professional_tone": true,
    "has_specific_metrics": true,
    "company_name_correct": true
}}

Be thorough but fair. Provide actionable feedback.
Return ONLY the JSON object, no other text."""


# ──────────────────────────────────────────────
# Main Agent Function (LangGraph Node)
# ──────────────────────────────────────────────

def qa_agent(state: ProposalState) -> dict:
    """
    QA Agent — LangGraph node function.

    Reads:  proposal_draft, proposal_sections, company_name, research_data
    Writes: qa_result, qa_score, revision_history, current_phase
    """
    proposal_draft = state.get("proposal_draft", "")
    proposal_sections = state.get("proposal_sections", {})
    company_name = state.get("company_name", "Unknown Company")
    research_data = state.get("research_data", {})
    revision_count = state.get("revision_count", 0)

    print("\n" + "=" * 60)
    print("  🔎 QA AGENT — Starting Review")
    print(f"  Prospect: {company_name}")
    print(f"  Draft Length: {len(proposal_draft):,} chars")
    print(f"  Revision: #{revision_count}")
    print("=" * 60)

    if not proposal_draft:
        print("  ❌ No proposal draft to review!")
        return {
            "qa_result": {
                "overall_score": 0.0,
                "critical_issues": ["No proposal draft was provided"],
            },
            "qa_score": 0.0,
            "current_phase": "qa_failed",
            "error": "No proposal draft to review",
        }

    try:
        # Build the QA prompt
        sections_list = ", ".join(ProposalConfig.SECTIONS)

        system_prompt = QA_SYSTEM_PROMPT.format(
            sections=sections_list,
            prospect_name=company_name,
        )

        review_prompt = (
            f"Review this B2B proposal and provide your quality assessment.\n\n"
            f"PROSPECT COMPANY: {company_name}\n"
            f"REVISION #: {revision_count}\n\n"
            f"RESEARCH DATA (for fact-checking):\n"
            f"{json.dumps(research_data, indent=2)[:2000]}\n\n"
            f"PROPOSAL TO REVIEW:\n"
            f"{'=' * 40}\n"
            f"{proposal_draft}\n"
            f"{'=' * 40}\n\n"
            f"Provide your detailed quality assessment as JSON."
        )

        # Call LLM
        print("\n🧠 Analyzing proposal quality...")
        llm = ModelConfig.get_llm()
        rate_limiter.wait_if_needed()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=review_prompt),
        ]

        response = llm.invoke(messages)
        response_text = response.content.strip()

        # Parse JSON
        print("\n📝 Parsing QA results...")

        cleaned_text = response_text
        if "```" in cleaned_text:
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1)
        
        cleaned_text = cleaned_text.strip()

        try:
            qa_result: QAResult = json.loads(cleaned_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
            if match:
                qa_result = json.loads(match.group(0))
            else:
                raise
        qa_score = qa_result.get("overall_score", 0.0)

        # Determine pass/fail
        if qa_score >= ProposalConfig.QA_AUTO_PASS_SCORE:
            status = "✅ AUTO-PASS"
            phase = "qa_passed"
        elif qa_score >= ProposalConfig.QA_AUTO_RETRY_SCORE:
            status = "⚠️ NEEDS REVISION"
            phase = "qa_needs_revision"
        else:
            status = "❌ MAJOR REWRITE"
            phase = "qa_needs_revision"

        # Build revision note
        critical = qa_result.get("critical_issues", [])
        minor = qa_result.get("minor_issues", [])
        suggestions = qa_result.get("suggestions", [])

        revision_note = (
            f"[Rev #{revision_count}] Score: {qa_score:.0%} | "
            f"Critical: {len(critical)} | Minor: {len(minor)} | "
            f"Suggestions: {len(suggestions)}"
        )

        print(f"\n  📊 Overall Score: {qa_score:.0%}")
        print(f"  📊 Status: {status}")
        print(f"  📊 Critical Issues: {len(critical)}")
        for i, issue in enumerate(critical, 1):
            print(f"     {i}. {issue}")
        print(f"  📊 Minor Issues: {len(minor)}")
        print(f"  📊 Suggestions: {len(suggestions)}")

        # Print section scores
        section_scores = qa_result.get("section_scores", {})
        if section_scores:
            print("\n  📋 Section Scores:")
            for section, score in section_scores.items():
                bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                print(f"     {section:35s} {bar} {score:.0%}")

        print("\n" + "=" * 60)
        print(f"  🔎 QA AGENT — Complete {status}")
        print("=" * 60)

        return {
            "qa_result": qa_result,
            "qa_score": qa_score,
            "revision_history": [revision_note],  # APPEND reducer
            "current_phase": phase,
        }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse QA results as JSON: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "qa_result": {},
            "qa_score": 0.0,
            "current_phase": "qa_failed",
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"QA agent error: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "qa_result": {},
            "qa_score": 0.0,
            "current_phase": "qa_failed",
            "error": error_msg,
        }