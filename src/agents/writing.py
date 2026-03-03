"""
Writing Agent — Generates a professional B2B proposal document.

Takes solution_mapping + research_data and writes a complete proposal
with all required sections from ProposalConfig.SECTIONS.

Flow:
    research_data + solution_mapping → Writing Agent → proposal_draft, proposal_sections
"""

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import ModelConfig, ProposalConfig, rate_limiter
from src.state.schema import ProposalState

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

WRITING_SYSTEM_PROMPT = """You are an expert B2B proposal writer for {company_name} ("{company_tagline}").

YOUR JOB:
Write a professional, compelling business proposal for a prospect company.

WRITING GUIDELINES:
1. Professional yet approachable tone
2. Focus on the prospect's specific pain points and how we solve them
3. Include specific metrics and results from case studies
4. Be concrete about timelines, deliverables, and expected outcomes
5. Use the prospect's company name throughout (personalization is key)
6. Each section should be 150-300 words
7. Use markdown formatting (headers, bullets, bold for emphasis)

REQUIRED SECTIONS:
{sections}

OUTPUT FORMAT:
Return a valid JSON object. Keys are section names, and values are the section content in markdown.

CRITICAL:
- Your entire response MUST be ONLY a valid JSON object.
- All values MUST be valid JSON strings (quoted with double quotes, newlines escaped as \\n).
- Do NOT include markdown headers (like '##' or '###') for the sections inside the JSON values.
- Ensure the JSON is properly closed.

Example:
{{
    "Executive Summary": "This is the summary...\\n\\nNext paragraph.",
    "Understanding Your Challenges": "We understand that..."
}}

Make the proposal specific, data-driven, and compelling.
Return ONLY the JSON object, no other text."""


# ──────────────────────────────────────────────
# Main Agent Function (LangGraph Node)
# ──────────────────────────────────────────────

def writing_agent(state: ProposalState) -> dict:
    """
    Writing Agent — LangGraph node function.

    Reads:  company_name, research_data, solution_mapping, matched_case_studies,
            industry, pain_points, user_request
    Writes: proposal_draft, proposal_sections, current_phase
    """
    company_name = state.get("company_name", "Unknown Company")
    research_data = state.get("research_data", {})
    solution_mapping = state.get("solution_mapping", {})
    matched_case_studies = state.get("matched_case_studies", [])
    industry = state.get("industry", "")
    pain_points = state.get("pain_points", [])
    user_request = state.get("user_request", "")
    requestor_name = state.get("requestor_name", "")

    print("\n" + "=" * 60)
    print("  ✍️  WRITING AGENT — Starting")
    print(f"  Prospect: {company_name}")
    print(f"  Sections: {len(ProposalConfig.SECTIONS)}")
    print("=" * 60)

    try:
        # Build the context for the LLM
        sections_list = "\n".join(
            f"  {i}. {s}" for i, s in enumerate(ProposalConfig.SECTIONS, 1)
        )

        system_prompt = WRITING_SYSTEM_PROMPT.format(
            company_name=ProposalConfig.YOUR_COMPANY_NAME,
            company_tagline=ProposalConfig.YOUR_COMPANY_TAGLINE,
            sections=sections_list,
        )

        # Compose the detailed writing brief
        pain_points_text = "\n".join(f"  - {pp}" for pp in pain_points)
        solutions_text = "\n".join(
            f"  - {pain}: {solution}"
            for pain, solution in solution_mapping.get("pain_to_solution", {}).items()
        )
        case_studies_text = "\n".join(
            f"  - {cs.get('case_study', 'N/A')} (for: {cs.get('pain_point', 'N/A')})"
            for cs in matched_case_studies
        )

        writing_brief = (
            f"Write a complete business proposal with these details:\n\n"
            f"PROSPECT: {company_name}\n"
            f"CONTACT: {requestor_name}\n"
            f"INDUSTRY: {industry}\n"
            f"REQUEST: {user_request}\n\n"
            f"RESEARCH SUMMARY:\n"
            f"  Overview: {research_data.get('company_overview', 'N/A')}\n"
            f"  Size: {research_data.get('employee_count', 'N/A')}\n"
            f"  HQ: {research_data.get('headquarters', 'N/A')}\n\n"
            f"PAIN POINTS:\n{pain_points_text}\n\n"
            f"OUR SOLUTIONS:\n{solutions_text}\n\n"
            f"RELEVANT CASE STUDIES:\n{case_studies_text}\n\n"
            f"FIT ANALYSIS:\n"
            f"  Score: {solution_mapping.get('fit_score', 'N/A')}\n"
            f"  Summary: {solution_mapping.get('fit_summary', 'N/A')}\n"
            f"  Package: {solution_mapping.get('recommended_package', 'N/A')}\n"
            f"  Timeline: {solution_mapping.get('estimated_timeline', 'N/A')}\n"
            f"  Value: {solution_mapping.get('estimated_value', 'N/A')}\n\n"
            f"Write each of the {len(ProposalConfig.SECTIONS)} required sections. "
            f"Return as a JSON object with section names as keys."
        )

        # Call LLM
        print("\n🧠 Generating proposal with LLM...")
        llm = ModelConfig.get_llm()
        rate_limiter.wait_if_needed()

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=writing_brief),
        ]

        response = llm.invoke(messages)
        response_text = response.content.strip()

        # Parse JSON
        print("\n📝 Parsing proposal sections...")

        cleaned_text = response_text
        if "```" in cleaned_text:
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1)
        
        cleaned_text = cleaned_text.strip()

        try:
            proposal_sections: dict[str, str] = json.loads(cleaned_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
            if match:
                proposal_sections = json.loads(match.group(0))
            else:
                raise

        # Assemble full proposal draft
        draft_parts = [
            f"# Business Proposal for {company_name}",
            f"*Prepared by {ProposalConfig.YOUR_COMPANY_NAME}*",
            f"*Date: {datetime.now(timezone.utc).strftime('%B %d, %Y')}*",
            "",
            "---",
            "",
        ]

        for section_name in ProposalConfig.SECTIONS:
            content = proposal_sections.get(section_name, "")
            if not content:
                # Try case-insensitive match
                for key, val in proposal_sections.items():
                    if key.lower() == section_name.lower():
                        content = val
                        break

            draft_parts.append(f"## {section_name}")
            draft_parts.append("")
            draft_parts.append(content if content else "*Section pending*")
            draft_parts.append("")
            draft_parts.append("---")
            draft_parts.append("")

        proposal_draft = "\n".join(draft_parts)

        sections_written = sum(
            1 for s in ProposalConfig.SECTIONS
            if proposal_sections.get(s) or any(
                k.lower() == s.lower() for k in proposal_sections
            )
        )

        print(f"\n  ✅ Sections Written: {sections_written}/{len(ProposalConfig.SECTIONS)}")
        print(f"  ✅ Draft Length: {len(proposal_draft):,} characters")

        print("\n" + "=" * 60)
        print("  ✍️  WRITING AGENT — Complete ✅")
        print("=" * 60)

        return {
            "proposal_draft": proposal_draft,
            "proposal_sections": proposal_sections,
            "current_phase": "writing_complete",
        }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse proposal sections as JSON: {e}"
        print(f"\n  ❌ {error_msg}")
        print(f"  ❌ Raw response (first 500 chars):\n{response_text[:500]}")
        return {
            "proposal_draft": "",
            "proposal_sections": {},
            "current_phase": "writing_failed",
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"Writing agent error: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "proposal_draft": "",
            "proposal_sections": {},
            "current_phase": "writing_failed",
            "error": error_msg,
        }
