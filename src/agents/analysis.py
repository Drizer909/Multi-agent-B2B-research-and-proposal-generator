"""
Analysis Agent — Maps research findings to solutions from our product catalog.

Takes research_data from the Research Agent and:
1. Matches pain points → our solutions (from product docs)
2. Finds relevant case studies (from RAG)
3. Calculates a fit score
4. Recommends a pricing package
5. Estimates timeline and value

Flow:
    research_data → Analysis Agent → solution_mapping, matched_case_studies
"""

import json
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import ModelConfig, ProposalConfig, rate_limiter
from src.state.schema import ProposalState, SolutionMapping
from src.tools.rag_search import rag_search_case_studies, rag_search_product_docs

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────

ANALYSIS_SYSTEM_PROMPT = """You are an expert B2B solution architect and sales strategist for {company_name}.
Your tagline: "{company_tagline}"

YOUR JOB:
Analyze a prospect's research data and map their pain points to our solutions.

You have access to:
1. The prospect's research data (company info, pain points, industry)
2. Our case studies (past success stories)
3. Our product documentation (features, pricing, capabilities)

ANALYSIS TASKS:
1. Map each pain point to a specific solution from our product catalog
2. Find the most relevant case studies for each pain point
3. Calculate a fit score (0.0 to 1.0) based on how well we can solve their problems
4. Recommend the best pricing package
5. Estimate implementation timeline
6. Estimate the business value we can deliver

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{{
    "pain_to_solution": {{
        "pain point text": "Our solution for this pain point"
    }},
    "pain_to_case_studies": {{
        "pain point text": ["relevant case study title 1"]
    }},
    "fit_score": 0.85,
    "fit_summary": "2-3 sentence explanation of why we're a good fit",
    "recommended_package": "Enterprise / Professional / Starter",
    "estimated_timeline": "e.g., 8-12 weeks for full implementation",
    "estimated_value": "e.g., $500K-$1M annual savings based on similar clients"
}}

Be specific and reference actual data from the case studies and product docs.
Return ONLY the JSON object, no other text."""


# ──────────────────────────────────────────────
# Tool Execution Helper
# ──────────────────────────────────────────────

def _execute_analysis_tools(
    pain_points: list[str],
    industry: str,
    user_request: str,
) -> str:
    """
    Search for case studies and product docs relevant to the prospect's needs.
    """
    results = []

    # 1. Search case studies for each pain point
    print("  📊 Searching case studies...")
    for pp in pain_points[:5]:  # Limit to top 5 to conserve API calls
        try:
            cases = rag_search_case_studies.invoke({
                "query": pp,
                "industry": industry,
            })
            results.append(f"=== CASE STUDIES for '{pp}' ===\n{cases}")
        except Exception as e:
            results.append(f"=== CASE STUDIES for '{pp}' ===\nSearch failed: {e}")

    # 2. Search product docs
    print("  📄 Searching product documentation...")
    try:
        products = rag_search_product_docs.invoke(user_request)
        results.append(f"\n=== PRODUCT DOCS ===\n{products}")
    except Exception as e:
        results.append(f"\n=== PRODUCT DOCS ===\nSearch failed: {e}")

    # 3. Search pricing info
    print("  💰 Searching pricing information...")
    try:
        pricing = rag_search_product_docs.invoke("pricing tiers packages enterprise")
        results.append(f"\n=== PRICING INFO ===\n{pricing}")
    except Exception as e:
        results.append(f"\n=== PRICING INFO ===\nSearch failed: {e}")

    return "\n".join(results)


# ──────────────────────────────────────────────
# Main Agent Function (LangGraph Node)
# ──────────────────────────────────────────────

def analysis_agent(state: ProposalState) -> dict:
    """
    Analysis Agent — LangGraph node function.

    Reads:  research_data, industry, pain_points, user_request
    Writes: solution_mapping, matched_case_studies, current_phase
    """
    research_data = state.get("research_data", {})
    industry = state.get("industry", "")
    pain_points = state.get("pain_points", [])
    user_request = state.get("user_request", "")
    company_name = state.get("company_name", "")

    print("\n" + "=" * 60)
    print("  🔍 ANALYSIS AGENT — Starting")
    print(f"  Prospect: {company_name}")
    print(f"  Industry: {industry}")
    print(f"  Pain Points: {len(pain_points)}")
    print("=" * 60)

    try:
        # Step 1: Gather relevant case studies and product docs
        print("\n📡 Phase 1: Searching knowledge base...")
        raw_analysis_data = _execute_analysis_tools(
            pain_points=pain_points,
            industry=industry,
            user_request=user_request,
        )

        # Step 2: Use LLM to synthesize analysis
        print("\n🧠 Phase 2: Analyzing with LLM...")
        llm = ModelConfig.get_llm()
        rate_limiter.wait_if_needed()

        system_prompt = ANALYSIS_SYSTEM_PROMPT.format(
            company_name=ProposalConfig.YOUR_COMPANY_NAME,
            company_tagline=ProposalConfig.YOUR_COMPANY_TAGLINE,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"Analyze this prospect and map their needs to our solutions.\n\n"
                f"PROSPECT COMPANY: {company_name}\n"
                f"INDUSTRY: {industry}\n"
                f"PAIN POINTS:\n" +
                "\n".join(f"  - {pp}" for pp in pain_points) +
                f"\n\nRESEARCH DATA:\n{json.dumps(research_data, indent=2)}\n\n"
                f"INTERNAL KNOWLEDGE (case studies & product docs):\n{raw_analysis_data}\n\n"
                f"Now map each pain point to our solutions, find matching case studies, "
                f"and provide your analysis as JSON."
            )),
        ]

        response = llm.invoke(messages)
        response_text = response.content.strip()

        # Step 3: Parse JSON
        print("\n📝 Phase 3: Parsing structured output...")

        cleaned_text = response_text
        if "```" in cleaned_text:
            import re
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_text, re.DOTALL)
            if match:
                cleaned_text = match.group(1)
        
        cleaned_text = cleaned_text.strip()

        try:
            analysis: SolutionMapping = json.loads(cleaned_text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
            if match:
                analysis = json.loads(match.group(0))
            else:
                raise

        # Extract matched case studies as list of dicts for state
        matched_case_studies = []
        for pain, cases in analysis.get("pain_to_case_studies", {}).items():
            for case in cases:
                matched_case_studies.append({
                    "pain_point": pain,
                    "case_study": case,
                })

        fit_score = analysis.get("fit_score", 0.0)

        print(f"\n  ✅ Fit Score: {fit_score:.0%}")
        print(f"  ✅ Recommended Package: {analysis.get('recommended_package', 'N/A')}")
        print(f"  ✅ Solutions Mapped: {len(analysis.get('pain_to_solution', {}))}")
        print(f"  ✅ Case Studies Matched: {len(matched_case_studies)}")

        print("\n" + "=" * 60)
        print("  🔍 ANALYSIS AGENT — Complete ✅")
        print("=" * 60)

        return {
            "solution_mapping": analysis,
            "matched_case_studies": matched_case_studies,
            "current_phase": "analysis_complete",
        }

    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse analysis as JSON: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "solution_mapping": {},
            "matched_case_studies": [],
            "current_phase": "analysis_failed",
            "error": error_msg,
        }
    except Exception as e:
        error_msg = f"Analysis agent error: {e}"
        print(f"\n  ❌ {error_msg}")
        return {
            "solution_mapping": {},
            "matched_case_studies": [],
            "current_phase": "analysis_failed",
            "error": error_msg,
        }